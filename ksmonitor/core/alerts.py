from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

from ksmonitor.adapters.kiwoom import KiwoomEndpoint
from ksmonitor.core import market_time

if TYPE_CHECKING:
    from ksmonitor.core.protocols import RestResponseOutput

logger = logging.getLogger(__name__)


class BaseAlert(ABC):
    """Base class for all alerts.

    Alerts are stateful: `ingest()` is called by the polling loop for every new
    response on the alert's subscription so the alert can maintain its own
    incremental state (per-ticker caches, rolling aggregates, etc.).
    `evaluate()` is called when its bucket/interval completes and reads only
    that cached state.

    Subclasses should exclusively use positional arguments to cleanly integrate
    with `TelegramBot`'s alert registration mechanism.

    `check()` is the scheduler entry point; it enforces cooldown and calls
    `evaluate` / `format_message`.

    Identity (`__hash__` / `__eq__`) is value-based on `(type_key, spec())` so
    that two instances constructed with the same args are interchangeable as
    dict/set keys. `name` is reserved for human-readable strings (logs, user
    messages) and intentionally excluded from identity.
    """

    type_key: ClassVar[str]

    def __init__(
        self,
        name: str,
        endpoint: KiwoomEndpoint,
        *,
        endpoint_params: dict[str, str] | None = None,
        cooldown_minutes: float = 0.0,
    ) -> None:
        self.name = name
        self.endpoint = endpoint
        self.endpoint_params = dict(endpoint_params or {})
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_fired: datetime | None = None

    def __hash__(self) -> int:
        return hash((self.type_key, self.spec()))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, BaseAlert)
            and self.type_key == other.type_key
            and self.spec() == other.spec()
        )

    def next_eval_time(self, now: datetime) -> datetime:
        """Return the next time this alert wants to be evaluated.
        Used by the scheduler to compute sleep duration.
        Subclasses override to express bucket/interval boundaries.
        """
        return now

    def is_due(self, now: datetime) -> bool:
        """Return True if this alert should be evaluated now.
        Subclasses may override to check bucket transitions, elapsed time, etc.
        """
        return True

    def check(self) -> str | None:
        """Run evaluation with cooldown enforcement. Returns message or None."""
        now = datetime.now()

        if self._last_fired and now - self._last_fired < self._cooldown:
            return None

        event = self.evaluate()
        if not event:
            return None

        self._last_fired = now
        message = self.format_message(event)
        logger.info(f"Alert {self.name!r} fired")
        return message

    @abstractmethod
    def ingest(self, output: RestResponseOutput) -> None:
        """Update internal state from a newly-polled response."""
        raise NotImplementedError()

    @abstractmethod
    def evaluate(self):
        """Return a subclass-defined event describing what fired, or `None` /
        a falsy value if no condition was met.

        May mutate dedup-tracking state (e.g. a per-bucket triggered set) so
        the same condition does not re-fire within the same evaluation window.
        Must NOT mutate ingestion state (`_latest`, `_bucket_start`, etc.).
        """
        raise NotImplementedError()

    @abstractmethod
    def format_message(self, event) -> str:
        """Format the alert message for the given event from `evaluate`."""
        raise NotImplementedError()

    @abstractmethod
    def spec(self) -> tuple[str | float, ...]:
        """Positional constructor args sufficient to reconstruct this alert.

        Used as the value-based identity key (with `type_key`) and as the
        serialization payload for `TelegramBot.save_user_configs`.
        """
        raise NotImplementedError()


@dataclass(slots=True)
class _TickerSample:
    polled_at: datetime
    value: float  # KRW
    code: str  # stock code
    name: str  # 종목명, cached for message formatting


class TradeValue(BaseAlert):
    """Fires when 거래대금 increases by at least `threshold_krw` across a
    `window_minutes`-wide bucket boundary (aligned to market open) for any
    ticker. Within-bucket growth alone never fires; the alert only triggers
    on the first sample of a new bucket whose delta from the prior bucket's
    last sample meets threshold.

    거래대금 (`trde_prica`) is cumulative; if a sample's value drops below the
    previous latest (e.g. a new trading day), the baseline is reset to the
    post-reset value.
    """

    type_key = "거래대금"

    def __init__(
        self,
        threshold_krw: float,
        window_minutes: int = 1,
        cooldown_minutes: float = 0.0,
    ) -> None:
        self.threshold_krw = threshold_krw
        self.window_minutes = window_minutes
        name = f"거래대금 {window_minutes}분봉 {self._number_to_natural(threshold_krw)}원 돌파"
        super().__init__(
            name=name,
            endpoint=KiwoomEndpoint.거래대금상위요청,
            cooldown_minutes=cooldown_minutes,
        )

        self._latest: dict[str, _TickerSample] = {}
        self._bucket_start: dict[str, _TickerSample] = {}
        self._last_fired_per_ticker: dict[str, datetime] = {}
        # Bucket identity per ticker, kept separate from sample timestamps so
        # baselines adopted from the prior bucket's last sample don't trigger
        # spurious bucket-changed detections on subsequent same-bucket polls.
        self._current_bucket: dict[str, datetime] = {}
        self._triggered_this_bucket: set[str] = set()
        # bucket index for detecting transitions
        self._last_eval_bucket: int | None = None

    def check(self) -> str | None:
        if not self._latest:
            return None

        now = max(s.polled_at for s in self._latest.values())
        current_bucket = market_time.bucket_index(now, minutes=self.window_minutes)
        self._last_eval_bucket = current_bucket

        fired = self.evaluate()
        if not fired:
            return None

        # Per-ticker cooldown
        should_fire = []
        for f in fired:
            last_fired = self._last_fired_per_ticker.get(f)
            if last_fired is None or now - last_fired >= self._cooldown:
                should_fire.append(f)

        if not should_fire:
            return None

        for f in should_fire:
            self._last_fired_per_ticker[f] = now

        message = self.format_message(should_fire)
        logger.info(f"Alert {self.name!r} fired")
        return message

    def is_due(self, now: datetime) -> bool:
        """Return True if we've entered a new bucket since the last evaluation."""
        current_bucket = market_time.bucket_index(now, minutes=self.window_minutes)
        if self._last_eval_bucket is None or current_bucket > self._last_eval_bucket:
            return True
        return False

    def next_eval_time(self, now: datetime) -> datetime:
        """Return the earliest time the next bucket can be fully evaluated.
        Adds a small buffer to account for network latency.
        """
        bucket_end = market_time.bucket_start(
            now, minutes=self.window_minutes
        ) + timedelta(minutes=self.window_minutes)
        # 200ms buffer to ensure all polling data from the bucket is received
        # (prevents race condition)
        return bucket_end + timedelta(milliseconds=200)

    def ingest(self, output: RestResponseOutput) -> None:
        polled_at = output.polled_at
        # Response is a list-shaped output: parallel lists for each field
        tickers: list[str] = output.stk_cd  # type: ignore[attr-defined]
        names: list[str] = output.stk_nm  # type: ignore[attr-defined]
        values: list[float] = output.trde_prica  # type: ignore[attr-defined]

        new_bucket = market_time.bucket_start(polled_at, minutes=self.window_minutes)
        for ticker, stk_nm, raw_value in zip(tickers, names, values):
            sample = _TickerSample(
                polled_at=polled_at,
                # Kiwoom returns trde_prica in 백만원 units (1e6);
                # normalize to KRW at ingest
                value=raw_value * 1e6,
                code=ticker,
                name=stk_nm,
            )
            prev_latest = self._latest.get(ticker)
            prev_bucket = self._current_bucket.get(ticker)

            is_reset = prev_latest is not None and sample.value < prev_latest.value
            bucket_changed = prev_bucket is not None and prev_bucket != new_bucket

            if is_reset:
                # Counter went backwards (eg. new day)
                # baseline tracks the reset value so subsequent growth is
                # measured from the post-reset floor.
                self._bucket_start[ticker] = sample
                self._triggered_this_bucket.discard(ticker)
            elif bucket_changed:
                # Bucket rollover -- baseline is the prior bucket's last sample.
                self._bucket_start[ticker] = prev_latest  # type: ignore[assignment]
                self._triggered_this_bucket.discard(ticker)

            # First sample for a ticker
            # (prev_bucket is None and not is_reset):
            # leave `_bucket_start` unset so within-first-bucket growth
            # cannot fire — alerting begins after the first bucket transition.

            self._latest[ticker] = sample
            self._current_bucket[ticker] = new_bucket

    def evaluate(self) -> list[str] | None:
        """Return ticker codes that crossed threshold this evaluation, or None."""
        fired: list[str] = []
        deltas = []
        for ticker, latest in self._latest.items():
            if ticker in self._triggered_this_bucket:
                continue
            baseline = self._bucket_start.get(ticker)
            if baseline is None:
                continue

            delta = latest.value - baseline.value
            if delta >= self.threshold_krw:
                self._triggered_this_bucket.add(ticker)
                fired.append(ticker)
                deltas.append(delta)

        if fired:
            # sort tickers, highest delta first
            fired = [f for _, f in sorted(zip(deltas, fired), reverse=True)]

        return fired or None

    @staticmethod
    def _number_to_natural(num: float) -> str:
        if num >= 1_000_000_000_000:
            return f"{num / 1_000_000_000_000:.1f}조"
        elif num >= 100_000_000:
            return f"{num / 100_000_000:.1f}억"
        elif num >= 10_000:
            return f"{num / 10_000:.1f}만"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}천"
        else:
            return str(num)

    def spec(self) -> tuple[float, int, float]:
        return (
            self.threshold_krw,
            self.window_minutes,
            self._cooldown.total_seconds() / 60,
        )

    def format_message(self, event: list[str]) -> str:
        polled_at = max(self._latest[t].polled_at for t in event).strftime(
            "%m/%d %H:%M:%S"
        )

        lines = [f"[{polled_at}]", self.name]
        for ticker in event:
            latest = self._latest[ticker]
            baseline = self._bucket_start[ticker]
            delta = latest.value - baseline.value
            lines.append(
                f"~~~ {latest.name} ({ticker}) ~~~\n"
                f"{self.window_minutes}분 거래대금: {self._number_to_natural(delta)}원\n"
                f"상승률: {delta / baseline.value * 100:.2f}%\n"
                f"누적 거래대금: {self._number_to_natural(latest.value)}원"
            )

        return "\n".join(lines) + "\n"

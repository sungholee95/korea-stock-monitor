from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from ksmonitor.core.alerts import TradeValue
from ksmonitor.core.protocols import RestResponseOutput


@dataclass
class _FakeTradePriceRankOutput:
    polled_at: datetime = field(default_factory=datetime.now)
    stk_cd: list[str] = field(default_factory=list)
    stk_nm: list[str] = field(default_factory=list)
    trde_prica: list[float] = field(default_factory=list)


def _output(
    polled_at: datetime, rows: list[tuple[str, str, float]]
) -> RestResponseOutput:
    """cast `_FakeTradePriceRankOutput` as `RestResponseOutput`
    to suppress linter warnings.
    """

    return cast(
        RestResponseOutput,
        _FakeTradePriceRankOutput(
            stk_cd=[r[0] for r in rows],
            stk_nm=[r[1] for r in rows],
            trde_prica=[r[2] for r in rows],
            polled_at=polled_at,
        ),
    )


class TestTradeValueBucketLogic:
    def test_first_ingest_never_fires(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.2)],
            )
        )
        assert not alert.evaluate()

    def test_no_fire_below_threshold(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.5)],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 30),
                [("005930", "삼성전자", threshold / 1e6 * 1.01)],
            )
        )

        # threshold * 1.01 - threshold * 0.5 < threshold
        assert not alert.evaluate()

    def test_no_fire_when_delta_crosses_threshold_within_bucket(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.01)],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 20),
                [("005930", "삼성전자", threshold / 1e6 * 2.05)],
            )
        )

        assert not alert.evaluate()

    def test_fires_when_delta_crosses_threshold_end_of_bucket(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.01)],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 20),
                [("005930", "삼성전자", threshold / 1e6 * 2.05)],
            )
        )

        assert alert.evaluate()

    def test_fires_exactly_at_end_of_bucket(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.01)],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 0),
                [("005930", "삼성전자", threshold / 1e6 * 2.05)],
            )
        )

        assert alert.evaluate()

    def test_multiple_tickers_crosses_threshold(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [
                    ("005930", "삼성전자", threshold / 1e6 * 0.2),
                    ("000660", "SK하이닉스", threshold / 1e6 * 0.3),
                ],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 30),
                [
                    ("005930", "삼성전자", threshold / 1e6 * 1.3),
                    ("000660", "SK하이닉스", threshold / 1e6 * 1.5),
                ],
            )
        )

        event = alert.evaluate()
        assert event
        msg = alert.format_message(event)
        assert all(m in msg for m in ("삼성전자", "005930", "SK하이닉스", "000660"))

    def test_no_tickers_crosses_threshold(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [
                    ("005930", "삼성전자", threshold / 1e6 * 0.3),
                    ("000660", "SK하이닉스", threshold / 1e6 * 0.4),
                ],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 30),
                [
                    ("005930", "삼성전자", threshold / 1e6 * 0.8),
                    ("000660", "SK하이닉스", threshold / 1e6 * 0.9),
                ],
            )
        )
        assert not alert.evaluate()

    def test_no_refire_within_same_bucket(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.1)],
            )
        )

        # fires once here because new bucket + crosses threshold
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 30),
                [("005930", "삼성전자", threshold / 1e6 * 1.1)],
            )
        )
        assert alert.evaluate()

        # Keep growing within the same bucket; should not re-fire
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 45),
                [("005930", "삼성전자", threshold / 1e6 * 3)],
            )
        )
        assert not alert.evaluate()

    def test_bucket_rollover_resets_triggered_state(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        # Bucket 0 baseline
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.5)],
            )
        )
        # First poll of bucket 1 snaps bucket 0 latest as baseline; delta crosses threshold
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.5)],
            )
        )
        assert alert.evaluate(), 1

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 50),
                [("005930", "삼성전자", threshold / 1e6 * 2.6)],
            )
        )
        assert not alert.evaluate(), 2

        # First poll of bucket 2 resets triggered state; delta crosses threshold again
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 2, 10),
                [("005930", "삼성전자", threshold / 1e6 * 3.5)],
            )
        )
        assert not alert.evaluate(), 3

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 2, 50),
                [("005930", "삼성전자", threshold / 1e6 * 3.7)],
            )
        )
        assert alert.evaluate(), 4

    def test_fires_multiple_buckets_later(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.1)],
            )
        )

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.1)],
            )
        )
        assert alert.evaluate()

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 2, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.5)],
            )
        )
        assert not alert.evaluate()

        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 5, 10),
                [("005930", "삼성전자", threshold / 1e6 * 3.1)],
            )
        )
        assert alert.evaluate()

    def test_counter_reset_within_bucket(self):
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        # Bucket 0 establishes prior-bucket value
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.5)],
            )
        )
        # Bucket 1 first poll: baseline = bucket 0 last (0.5T); delta = T
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.5)],
            )
        )
        assert alert.evaluate()

        # Same bucket 1, counter goes backward — `is_reset` resets baseline
        # to the post-reset value and clears the triggered set.
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 30),
                [("005930", "삼성전자", threshold / 1e6 * 0.1)],
            )
        )
        # Same bucket 1, growth from the reset baseline crosses threshold
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 1, 50),
                [("005930", "삼성전자", threshold / 1e6 * 1.2)],
            )
        )
        # delta = (1.2 - 0.1) * T ≥ T -> fires again
        assert alert.evaluate()

    def test_resets_on_new_day(self):
        """`is_reset` takes precedence over `bucket_changed` across a day boundary,
        so day 2's baseline becomes the post-reset value (not day 1's last sample)."""
        threshold = 10_000_000_000
        alert = TradeValue(threshold_krw=threshold, window_minutes=1)

        # Day 1: small opening sample, then large end-of-day cumulative value
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 0.5)],
            )
        )
        alert.ingest(
            _output(
                datetime(2026, 1, 1, 14, 30, 10),
                [("005930", "삼성전자", threshold / 1e6 * 5)],
            )
        )
        assert alert.evaluate(), 1

        # Day 2 first sample: cumulative counter resets. Both is_reset
        # (5.0 -> 1.1) and bucket_changed (date1 -> date2) are True;
        # is_reset wins -> baseline = 1.1*T, not 5.0*T.
        alert.ingest(
            _output(
                datetime(2026, 1, 2, 8, 0, 10),
                [("005930", "삼성전자", threshold / 1e6 * 1.1)],
            )
        )
        assert not alert.evaluate(), 2

        # Day 2 next bucket: growth from the new-day floor crosses threshold.
        # If the baseline had been mistakenly set to day 1's last value (5.0*T),
        # this delta would be negative and no fire — so the assertion below
        # also verifies the post-reset baseline.
        alert.ingest(
            _output(
                datetime(2026, 1, 2, 8, 1, 30),
                [("005930", "삼성전자", threshold / 1e6 * 2.2)],
            )
        )
        assert alert.evaluate(), 3


class TestBaseAlertScheduling:
    def test_is_due_only_once_per_bucket(self):
        alert = TradeValue(threshold_krw=1_000_000, window_minutes=1)

        # First time: is_due (no prior evaluation)
        t1 = datetime(2026, 1, 1, 8, 1, 30)
        assert alert.is_due(t1)

        # Manually mark bucket 1 as evaluated (avoids real datetime.now())
        alert._last_eval_bucket = 1

        # Still within same bucket: not due
        t1_later = datetime(2026, 1, 1, 8, 1, 45)
        assert not alert.is_due(t1_later)

        # New bucket: due again
        t2 = datetime(2026, 1, 1, 8, 2, 5)
        assert alert.is_due(t2)

    def test_next_eval_time_returns_bucket_end(self):
        alert = TradeValue(threshold_krw=1_000_000, window_minutes=1)

        # At 08:01:30, next eval is at the end of bucket [08:01, 08:02)
        t = datetime(2026, 1, 1, 8, 1, 30)
        next_time = alert.next_eval_time(t)
        # End of bucket + 200ms buffer
        assert next_time == datetime(2026, 1, 1, 8, 2, 0, 200000)

    def test_next_eval_time_with_5min_window(self):
        alert = TradeValue(threshold_krw=1_000_000, window_minutes=5)

        # At 08:07:15, we're in [08:05, 08:10), next eval at 08:10:00.200
        t = datetime(2026, 1, 1, 8, 7, 15)
        next_time = alert.next_eval_time(t)
        assert next_time == datetime(2026, 1, 1, 8, 10, 0, 200000)

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

import requests

from ksmonitor.adapters._shared import Method
from ksmonitor.core.datastore import DataStore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from ksmonitor.core.alerts import BaseAlert

    from .auth import KiwoomAuth
    from .endpoints import KiwoomEndpoint, KiwoomRestRequest, KiwoomRestResponse


_DEFAULT_DATA_PATH = Path("~").expanduser() / ".ksmonitor" / "data" / "datastore.db"


class KiwoomSubscription:
    def __init__(
        self,
        request_spec: type[KiwoomRestRequest],
        auth: KiwoomAuth,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        logger.debug(
            f"Constructing `KiwoomSubscription` for endpoint: {request_spec._endpoint.name!r}"
        )

        self.auth = auth
        self.query_params = query_params or {}
        self.req = request_spec(auth=auth, **self.query_params)
        self.response_spec = request_spec._response_spec

    def execute(self) -> KiwoomRestResponse:
        logger.debug(
            f"Executing Kiwoom REST request for endpoint: {self.req._endpoint.name!r}"
        )
        try:
            raw_response = requests.request(**self.req.build_request())
            logger.debug(
                f"Received response with status code: {raw_response.status_code}"
            )
            raw_response.raise_for_status()
        except requests.RequestException as exc:
            err_msg = (
                f"Failed to execute Kiwoom REST request for "
                f"{self.req._endpoint.name!r}: {exc}"
            )
            logger.exception(err_msg)
            raise

        response = self.response_spec(raw_response)
        if response.has_next_page():
            logger.warning(
                f"Pagination is not implemented yet for Kiwoom endpoint "
                f"{self.req._endpoint.name!r}; returning the first page only"
            )

        return response


class _KiwoomRestClient:
    def __init__(self, auth: KiwoomAuth, poll_rate: float):
        logger.info(f"Initializing _KiwoomRestClient with refresh rate: {poll_rate} s")
        self.auth = auth
        self.poll_rate = poll_rate
        self._subscribed: dict[str, KiwoomSubscription] = {}

    def _enforce_rate_limit(self) -> None:
        n_subs = len(self._subscribed)
        if n_subs == 0:
            return

        rate = self.poll_rate
        if rate == 0:
            err = "Refresh rate must be greater than 0"
            logger.error(err)
            raise ValueError(err)

        calls_per_sec = n_subs / rate
        if self.auth.config.is_paper:
            if calls_per_sec > 2:
                err_msg = (
                    f"Rate limit exceeded: "
                    f"{n_subs} subscriptions / {rate}s refresh rate "
                    f"= {calls_per_sec:.2f} calls/s > 2/s"
                )
                raise ValueError(err_msg)
        else:
            if calls_per_sec > 20:
                err_msg = (
                    f"Rate limit exceeded: "
                    f"{n_subs} subscriptions / {rate}s refresh rate "
                    f"= {calls_per_sec:.2f} calls/s > 20/s"
                )
                raise ValueError(err_msg)

    async def poll(self) -> AsyncGenerator[dict[str, KiwoomRestResponse | None], None]:
        while True:
            try:
                response = self.execute_all()
                await asyncio.sleep(self.poll_rate)
                yield response
            except asyncio.CancelledError:
                logger.info("Client stopped by user (KeyboardInterrupt)")
                break

    def execute_all(self) -> dict[str, KiwoomRestResponse | None]:
        responses: dict[str, KiwoomRestResponse | None] = {}
        for name, subscription in self._subscribed.items():
            try:
                responses[name] = subscription.execute()
                logger.debug(f"Executed subscription: {name}")
            except (requests.RequestException, ValueError) as exc:
                logger.error(f"Failed to execute subscription {name}: {exc}")
                responses[name] = None

        return responses

    def subscribe(
        self,
        endpoint: KiwoomEndpoint,
        *,
        name: str | None = None,
        query_params: dict[str, str] | None = None,
    ) -> KiwoomSubscription:
        name = name or endpoint.name
        logger.info(f"Subscribing to Kiwoom REST endpoint: {name}")
        logger.debug(f"Endpoint: {endpoint.value}, Query params: {query_params}")
        request_spec = endpoint.get_request_spec()

        if request_spec._endpoint.method not in (Method.GET, Method.POST):
            err_msg = f"Endpoint is not a REST endpoint: {endpoint}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        subscription = KiwoomSubscription(
            request_spec,
            self.auth,
            query_params=query_params,
        )
        self._subscribed[name] = subscription
        self._enforce_rate_limit()

        logger.info(f"Successfully subscribed to {name}")
        return subscription

    def unsubscribe(self, endpoint: KiwoomEndpoint | str) -> KiwoomSubscription | None:
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"Unsubscribing from Kiwoom REST endpoint: {name}")
        subscription = self._subscribed.pop(name, None)
        if subscription:
            logger.info(f"Successfully unsubscribed from {name}")
        else:
            logger.debug(f"Subscription {name} not found")

        return subscription


class _KiwoomWebSocketClient:
    def __init__(self, auth: KiwoomAuth, rate_limit_delay: float):
        logger.info(
            f"Initializing _KiwoomWebSocketClient with rate limit delay: {rate_limit_delay}s"
        )
        self.auth = auth
        self._uri = auth.get_ws_base_url()
        logger.debug(f"WebSocket URI: {self._uri}")
        self._connection: ClientConnection | None = None
        self._subscribed: list[KiwoomEndpoint] = []

    def subscribe(self, endpoint: KiwoomEndpoint):
        raise NotImplementedError("Kiwoom WebSocket client not yet implemented")

    def unsubscribe(self, endpoint: KiwoomEndpoint):
        logger.info(f"Unsubscribing from Kiwoom WebSocket endpoint: {endpoint.name}")
        raise NotImplementedError("Kiwoom WebSocket client not yet implemented")


class KiwoomClient:
    def __init__(
        self,
        auth: KiwoomAuth,
        rest_poll_rate: int | float = 60,
        data_path: Path = _DEFAULT_DATA_PATH,
        data_retention_days: int = 7,
    ):
        logger.info(
            f"Initializing KiwoomClient with REST polling rate: {rest_poll_rate}s"
        )
        self.auth = auth
        self.data_path = data_path
        self.rest_client = _KiwoomRestClient(auth, rest_poll_rate)
        self.ws_client = _KiwoomWebSocketClient(auth, rate_limit_delay=1)

        self._subscribed: dict[str, KiwoomSubscription] = {}
        self.datastore = DataStore(data_path, retention_days=data_retention_days)
        self.alerts: set[BaseAlert] = set()
        self._alerts_by_sub: dict[str, set[BaseAlert]] = {}
        self._alerts_changed = asyncio.Event()

    @staticmethod
    def _subscription_key(endpoint: KiwoomEndpoint, params: dict[str, str]) -> str:
        if not params:
            return endpoint.name
        joined = ",".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint.name}_{joined}"

    def _subscribe(
        self,
        endpoint: KiwoomEndpoint,
        name: str | None = None,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        name = name or endpoint.name
        if name in self._subscribed:
            logger.debug(f"Already subscribed to {name!r}; skipping")
            return

        match endpoint.method:
            case Method.GET | Method.POST:
                new_sub = self.rest_client.subscribe(
                    endpoint,
                    name=name,
                    query_params=query_params,
                )
            case Method.WEBSOCKET:
                raise NotImplementedError()
            case _:
                err_msg = (
                    f"Unsupported method {endpoint.method.name!r} for endpoint "
                    f"{endpoint}"
                )
                logger.error(err_msg)
                raise ValueError(err_msg)

        self._subscribed[name] = new_sub
        self.datastore.register(name, new_sub.response_spec._output_schema)
        logger.debug(f"Subscribed to {name!r} (via {endpoint.method.name!r})")

    def _unsubscribe(self, name: str) -> None:
        logger.debug(f"Unsubscribing from {name!r}")

        unsubbed = self._subscribed.pop(name, None)
        if unsubbed is not None:
            if unsubbed.req.method in (Method.GET, Method.POST):
                self.rest_client.unsubscribe(name)
            elif unsubbed.req.method == Method.WEBSOCKET:
                raise NotImplementedError()

            self.datastore.unregister(name)
            logger.debug(f"Unsubscribed from {name!r}")
        else:
            logger.debug(f"No subscription found for {name!r}")

    async def poll_loop(self) -> None:
        async for polled in self.rest_client.poll():
            for name, response in polled.items():
                if response is None:
                    continue

                self.datastore.update(name, response.output)

                for alert in self._alerts_by_sub.get(name, ()):
                    alert.ingest(response.output)

            self.datastore.save()

    async def alert_loop(self) -> AsyncGenerator[tuple[BaseAlert, str]]:
        while True:
            self._alerts_changed.clear()
            now = datetime.now()
            if self.alerts:
                next_due = min(alert.next_eval_time(now) for alert in self.alerts)
                sleep_secs = max(0.1, (next_due - now).total_seconds())
            else:
                # `None` -> wait indefinitely
                sleep_secs = None

            try:
                await asyncio.wait_for(self._alerts_changed.wait(), sleep_secs)
                # if alert changes, `_alert_changed.wait()` returns True, and
                # asyncio.wait_for also returns normally, triggering `continue`.
                # Otherwise, we wait for `sleep_secs` (computed from the registered
                # alerts) asyncio.TimeoutError is raised, and we move on to the
                # rest of the alert loop.
                continue
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                logger.info("Alert loop cancelled")
                break

            now = datetime.now()
            for alert in self.alerts:
                if not alert.is_due(now):
                    continue

                message = alert.check()
                if message:
                    logger.info(f"Alert triggered: {alert.name!r}")
                    yield alert, message

    def execute_all_rest(self) -> dict[str, KiwoomRestResponse | None]:
        return self.rest_client.execute_all()

    def register_alerts(self, *alerts: BaseAlert) -> None:
        for alert in alerts:
            key = self._subscription_key(alert.endpoint, alert.endpoint_params)
            if key not in self._subscribed:
                self._subscribe(
                    alert.endpoint,
                    name=key,
                    query_params=alert.endpoint_params,
                )
            self._alerts_by_sub.setdefault(key, set()).add(alert)
            self.alerts.add(alert)
            logger.info(f"Registered alert {alert.name!r} on {key!r}")

        self._alerts_changed.set()

    def unregister_alert(self, alert: BaseAlert) -> None:
        key = self._subscription_key(alert.endpoint, alert.endpoint_params)
        watchers = self._alerts_by_sub.get(key)
        if watchers is not None:
            watchers.discard(alert)
            if not watchers:
                self._alerts_by_sub.pop(key, None)
                self._unsubscribe(key)

        self.alerts.discard(alert)
        self._alerts_changed.set()
        logger.info(f"Unregistered alert {alert.name!r}")

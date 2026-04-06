from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

import requests

from ksmonitor.adapters._shared import Method
from ksmonitor.core.datastore import DataStore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from .auth import KISAuth
    from .endpoints import KISEndpoint, KISRestRequest, KISRestResponse


_DEFAULT_DATA_PATH = Path("~").expanduser() / ".ksmonitor" / "data" / "datastore.db"


class KISSubscription:
    def __init__(
        self,
        request_spec: type[KISRestRequest],
        auth: KISAuth,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        logger.debug(
            f"Constructing `KISSubscription` for endpoint: {request_spec._endpoint.name!r}"
        )

        self.auth = auth
        self.query_params = query_params or {}
        self.req = request_spec(auth=auth, **self.query_params)
        self.response_spec = request_spec._response_spec

    def execute(self) -> KISRestResponse:
        logger.debug(
            f"Executing KIS REST request for endpoint: {self.req._endpoint.name!r}"
        )
        try:
            raw_response = requests.request(**self.req.build_request())
            logger.debug(
                f"Received response with status code: {raw_response.status_code}"
            )
            raw_response.raise_for_status()
        except requests.RequestException as exc:
            err_msg = (
                f"Failed to execute KIS REST request for "
                f"{self.req._endpoint.name!r}: {exc}"
            )
            logger.exception(err_msg)
            raise

        response = self.response_spec(raw_response)
        if response.has_next_page():
            logger.warning(
                f"Pagination is not implemented yet for KIS endpoint "
                f"{self.req._endpoint.name!r}; returning the first page only"
            )

        return response


class _KISRestClient:
    def __init__(self, auth: KISAuth, refresh_rate: float):
        logger.info(f"Initializing _KISRestClient with refresh rate: {refresh_rate} s")
        self.auth = auth
        self.refresh_rate = refresh_rate
        self._subscribed: dict[str, KISSubscription] = {}

    def _enforce_rate_limit(self) -> None:
        n_subs = len(self._subscribed)
        if n_subs == 0:
            return

        rate = self.refresh_rate
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

    async def poll(self) -> AsyncGenerator[dict[str, KISRestResponse | None], None]:
        self._enforce_rate_limit()

        while True:
            try:
                response = self.execute_all()
                await asyncio.sleep(self.refresh_rate)
                yield response
            except asyncio.CancelledError:
                logger.info("Client stopped by user (KeyboardInterrupt)")
                break

    def execute_all(self) -> dict[str, KISRestResponse | None]:
        responses: dict[str, KISRestResponse | None] = {}
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
        endpoint: KISEndpoint,
        *,
        name: str | None = None,
        query_params: dict[str, str] | None = None,
    ) -> KISSubscription:
        name = name or endpoint.name
        logger.info(f"Subscribing to KIS REST endpoint: {name}")
        logger.debug(f"Endpoint: {endpoint.value}, Query params: {query_params}")
        request_spec = endpoint.get_request_spec()

        if request_spec._endpoint.method not in (Method.GET, Method.POST):
            err_msg = f"Endpoint is not a REST endpoint: {endpoint}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        subscription = KISSubscription(
            request_spec,
            self.auth,
            query_params=query_params,
        )
        self._subscribed[name] = subscription
        logger.info(f"Successfully subscribed to {name}")
        return subscription

    def unsubscribe(self, endpoint: KISEndpoint | str) -> KISSubscription | None:
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"Unsubscribing from KIS REST endpoint: {name}")
        subscription = self._subscribed.pop(name, None)
        if subscription:
            logger.info(f"Successfully unsubscribed from {name}")
        else:
            logger.debug(f"Subscription {name} not found")

        return subscription


class _KISWebSocketClient:
    def __init__(self, auth: KISAuth, rate_limit_delay: float):
        logger.info(
            f"Initializing _KISWebSocketClient with rate limit delay: {rate_limit_delay}s"
        )
        self.auth = auth
        self._uri = auth.get_ws_base_url()
        logger.debug(f"WebSocket URI: {self._uri}")
        self._connection: ClientConnection | None = None
        self._subscribed: list[KISEndpoint] = []

    def subscribe(self, endpoint: KISEndpoint):
        raise NotImplementedError("KIS WebSocket client not yet implemented")

    def unsubscribe(self, endpoint: KISEndpoint):
        logger.info(f"Unsubscribing from KIS WebSocket endpoint: {endpoint.name}")
        raise NotImplementedError("KIS WebSocket client not yet implemented")


class KISClient:
    def __init__(
        self,
        auth: KISAuth,
        rest_refresh_rate: int | float = 60,
        data_path: Path = _DEFAULT_DATA_PATH,
    ):
        logger.info(
            f"Initializing KISClient with REST refresh rate: {rest_refresh_rate}s"
        )
        self.auth = auth
        self.data_path = data_path
        self.rest_client = _KISRestClient(auth, rest_refresh_rate)
        self.ws_client = _KISWebSocketClient(auth, rate_limit_delay=1)

        self._subscribed: dict[str, KISSubscription] = {}
        self.datastores: dict[str, DataStore] = {}

    def subscribe(
        self,
        endpoint: KISEndpoint,
        name: str | None = None,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        name = name or endpoint.name

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
        self.datastores[name] = DataStore.from_endpoint(
            name, new_sub.response_spec._output_schema
        )
        logger.debug(f"Subscribed to {name!r} (via {endpoint.method.name!r})")

    def unsubscribe(self, endpoint: KISEndpoint | str) -> None:
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.debug(f"Unsubscribing from {name!r}")

        unsubbed = self._subscribed.pop(name, None)
        if unsubbed is not None:
            if unsubbed.req.method in (Method.GET, Method.POST):
                self.rest_client.unsubscribe(name)
            elif unsubbed.req.method == Method.WEBSOCKET:
                raise NotImplementedError()

            self.datastores.pop(name)
            logger.debug(f"Unsubscribed from {name!r}")
        else:
            logger.debug(f"No subscription found for {name!r}")

    async def start(self) -> None:
        logger.info("Starting KISClient")
        async for polled in self.rest_client.poll():
            for name, response in polled.items():
                if response is None:
                    continue

                self.datastores[name].update(response.output)
                self.datastores[name].save_to_disk(self.data_path)

            logger.debug("Received new data from KIS REST client poll")

    def save(self) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        for store in self.datastores.values():
            store.save_to_disk(self.data_path)
        logger.info(f"Saved all datastores to `{self.data_path}`")

    def execute_all_rest(self) -> dict[str, KISRestResponse | None]:
        return self.rest_client.execute_all()

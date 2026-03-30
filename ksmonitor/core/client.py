from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

import requests

from ..adapters._base.endpoints import Endpoint, Method
from .datastore import DataStore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from ..adapters._base.auth import Auth
    from ..adapters.kis.endpoints import KISRestRequest, KISRestResponse
    from ..adapters.kiwoom.endpoints import KiwoomRestRequest, KiwoomRestResponse

    type RestRequest = KISRestRequest | KiwoomRestRequest
    type RestResponse = KISRestResponse | KiwoomRestResponse
    type RestRequestType = type[RestRequest]


_DEFAULT_DATA_PATH = Path("~").expanduser() / ".ksmonitor" / "data" / "datastore.db"


class Subscription:
    def __init__(
        self,
        request_spec: RestRequestType,
        auth: Auth,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        logger.debug(
            f"Constructing `Subscription` for endpoint: {request_spec._endpoint.name!r}"
        )

        self.auth = auth
        self.query_params = query_params or {}
        self.req = request_spec(auth=auth, **(query_params or {}))  # pyright: ignore[reportArgumentType]

        self.response_spec = request_spec._response_spec

    def execute(self) -> RestResponse:
        logger.debug(
            f"Executing REST request for endpoint: {self.req._endpoint.name!r}"
        )
        try:
            if self.req.method == Method.GET:
                raw_response = requests.get(
                    url=f"{self.auth.get_rest_base_url()}{self.req.api_path}",
                    headers=self.req.headers(),
                    params=self.req.query_params(),
                    timeout=10,
                )
            elif self.req.method == Method.POST:
                raw_response = requests.post(
                    url=f"{self.auth.get_rest_base_url()}{self.req.api_path}",
                    headers=self.req.headers(),
                    data=json.dumps(self.req.query_params()),
                    timeout=10,
                )
            logger.debug(
                f"Received response with status code: {raw_response.status_code}"
            )
            raw_response.raise_for_status()
        except requests.RequestException as e:
            err_msg = (
                f"Failed to execute REST request for {self.req._endpoint.name!r}: {e}"
            )
            logger.exception(err_msg)
            raise

        response = self.response_spec(raw_response)
        if response.has_next_page():
            # TODO: implement pagination auto-fetch logic
            raise NotImplementedError("Pagination auto-fetch not yet implemented")

        return response


class _RestClient:
    def __init__(self, auth: Auth, refresh_rate: float):
        logger.info(f"Initializing _RestClient with refresh rate: {refresh_rate} s")
        self.auth = auth
        self.refresh_rate = refresh_rate
        self._subscribed: dict[str, Subscription] = {}

    def _enforce_rate_limit(self):
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

    async def poll(self) -> AsyncGenerator[dict[str, RestResponse]]:
        self._enforce_rate_limit()

        while True:
            try:
                response = self.execute_all()
                await asyncio.sleep(self.refresh_rate)
                yield response
            except asyncio.CancelledError:
                logger.info("Client stopped by user (KeyboardInterrupt)")
                break

    def execute_all(self) -> dict[str, RestResponse]:
        responses: dict[str, RestResponse] = {}
        for name, subscription in self._subscribed.items():
            try:
                responses[name] = subscription.execute()
                logger.debug(f"Executed subscription: {name}")
            except (requests.RequestException, ValueError) as e:
                # TODO: improve error handling, depending on the type
                logger.error(f"Failed to execute subscription {name}: {e}")
                continue

        return responses

    def subscribe(
        self,
        endpoint: Endpoint,
        *,
        name: str | None = None,
        query_params: dict[str, str] | None = None,
    ) -> Subscription:
        name = name or endpoint.name
        logger.info(f"Subscribing to REST endpoint: {name}")
        logger.debug(f"Endpoint: {endpoint.value}, Query params: {query_params}")
        request_spec: RestRequestType = endpoint.get_request_spec()  # pyright: ignore[reportAssignmentType]

        if request_spec._endpoint.method not in (Method.GET, Method.POST):
            err_msg = f"Endpoint is not a REST endpoint: {endpoint}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        subscription = Subscription(
            request_spec,
            self.auth,
            query_params=query_params,
        )
        self._subscribed[name] = subscription
        logger.info(f"Successfully subscribed to {name}")
        return subscription

    def unsubscribe(self, endpoint: Endpoint | str) -> Subscription | None:
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"Unsubscribing from REST endpoint: {name}")
        subscription = self._subscribed.pop(name, None)
        if subscription:
            logger.info(f"Successfully unsubscribed from {name}")
        else:
            logger.debug(f"Subscription {name} not found")

        return subscription


class _WebSocketClient:
    def __init__(self, auth: Auth, rate_limit_delay):
        logger.info(
            f"Initializing _WebSocketClient with rate limit delay: {rate_limit_delay}s"
        )
        self.auth = auth
        self._uri = auth.get_ws_base_url()
        logger.debug(f"WebSocket URI: {self._uri}")
        self._connection: ClientConnection | None = None
        self._subscribed: list[Endpoint] = []

    def subscribe(self, endpoint: Endpoint):
        raise NotImplementedError("WebSocket client not yet implemented")

        logger.info(f"Subscribing to WebSocket endpoint: {endpoint.name}")
        if len(self._subscribed) == 40:
            err_msg = (
                f"Max 40 WebSocket subscriptions reached, cannot add {endpoint.name}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)
        logger.debug(f"Current WebSocket subscriptions: {len(self._subscribed)}/40")

    def unsubscribe(self, endpoint: Endpoint):
        logger.info(f"Unsubscribing from WebSocket endpoint: {endpoint.name}")
        # generate unsubscription message and send to ws
        pass


class Client:
    def __init__(
        self,
        auth: Auth,
        rest_refresh_rate: int | float = 60,
        data_path: Path = _DEFAULT_DATA_PATH,
    ):
        logger.info(f"Initializing Client with REST refresh rate: {rest_refresh_rate}s")
        self.auth = auth
        self.data_path = data_path
        self.rest_client = _RestClient(auth, rest_refresh_rate)
        self.ws_client = _WebSocketClient(auth, rate_limit_delay=1)

        self._subscribed: dict[str, Subscription] = {}
        self.datastores: dict[str, DataStore] = {}

    def subscribe(self, endpoint: Endpoint, name: str | None = None, **kwargs):
        name = name or endpoint.name

        match endpoint.method:
            case Method.GET | Method.POST:
                new_sub = self.rest_client.subscribe(endpoint, name=name, **kwargs)
            case Method.WEBSOCKET:
                raise NotImplementedError()
                new_sub = self.ws_client.subscribe(endpoint)
            case _:
                err_msg = f"Unsupported method {endpoint.method.name!r} for endpoint {endpoint}"
                logger.error(err_msg)
                raise ValueError(err_msg)

        self._subscribed[name] = new_sub
        self.datastores[name] = DataStore.from_endpoint(
            name, new_sub.response_spec._output_schema
        )
        logger.debug(f"Subscribed to {name!r} (via {endpoint.method.name!r})")

    def unsubscribe(self, endpoint: Endpoint | str):
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.debug(f"Unsubscribing from {name!r}")

        unsubbed = self._subscribed.pop(name, None)
        if unsubbed is not None:
            if unsubbed.req.method in (Method.GET, Method.POST):
                self.rest_client.unsubscribe(name)
            elif unsubbed.req.method == Method.WEBSOCKET:
                raise NotImplementedError()
                self.ws_client.unsubscribe(name)

            self.datastores.pop(name)
            logger.debug(f"Unsubscribed from {name!r}")
        else:
            logger.debug(f"No subscription found for {name!r}")

    async def start(self):
        logger.info("Starting Client")
        async for polled in self.rest_client.poll():
            for name, response in polled.items():
                self.datastores[name].update(response)
                self.datastores[name].save_to_disk(self.data_path)

            logger.debug("Received new data from REST client poll")

    def save(self) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        for store in self.datastores.values():
            store.save_to_disk(self.data_path)
        logger.info(f"Saved all datastores to `{self.data_path}`")

    def execute_all_rest(self) -> dict[str, RestResponse]:
        return self.rest_client.execute_all()

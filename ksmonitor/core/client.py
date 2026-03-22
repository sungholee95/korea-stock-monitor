from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import requests

from ..adapters.kis.endpoints import Method, get_request_spec

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from ..adapters.kis.auth import KISAuth
    from ..adapters.kis.endpoints import KISEndpoint, RestResponse

    type RestRequestType = type[RestResponse]


class Subscription:
    def __init__(
        self,
        request_spec: RestRequestType,
        auth: KISAuth,
        *,
        query_params: dict[str, str] | None = None,
    ) -> None:
        logger.debug(
            f"Constructing `Subscription` for endpoint: {request_spec._endpoint.tr_id!r}"
        )

        self.auth = auth
        self.query_params = query_params or {}
        self.req = request_spec(auth=auth, **(query_params or {}))
        if self.req.method not in (Method.GET, Method.WEBSOCKET):
            # TODO: unsure if this is true?
            raise ValueError("Only GET and WEBSOCKET endpoints can be subscribed to")

        self.response_spec = request_spec._response_spec

    def execute(self) -> RestResponse:
        logger.debug(f"Executing REST request for endpoint: {self.req.tr_id}")
        try:
            response = requests.request(
                method=self.req.method.name,
                url=f"{self.auth.get_rest_base_url()}{self.req.api_path}",
                headers=self.req.headers(),
                params=self.req.query_params(),
                timeout=10,
            )
            logger.debug(f"Received response with status code: {response.status_code}")
        except requests.RequestException as e:
            err_msg = f"Failed to execute REST request for {self.req.tr_id}: {e}"
            logger.exception(err_msg)
            raise

        response = self.response_spec(response)
        if response.has_next_page():
            # TODO: implement pagination auto-fetch logic
            logger.debug(
                f"Pagination detected (tr_cont={response.tr_cont!r}); "
                f"pagination auto-fetch not yet implemented"
            )
            raise NotImplementedError("Pagination auto-fetch not yet implemented")

        return response


class _KISRestClient:
    def __init__(self, auth: KISAuth, refresh_rate: int | float):
        logger.info(f"Initializing _KISRestClient with refresh rate: {refresh_rate} s")
        self.auth = auth
        self.refresh_rate = refresh_rate
        self._subscribed: dict[str, Subscription] = {}

    async def poll(self) -> dict[str, RestResponse | None]:
        await asyncio.sleep(self.refresh_rate)
        return self.execute_all()

    def execute_all(self) -> dict[str, RestResponse | None]:
        responses: dict[str, RestResponse | None] = {}
        for name, subscription in self._subscribed.items():
            try:
                responses[name] = subscription.execute()
                logger.debug(f"Executed subscription: {name}")
            except (requests.RequestException, ValueError) as e:
                logger.error(f"Failed to execute subscription {name}: {e}")
                responses[name] = None
                continue

        return responses

    def subscribe(
        self,
        endpoint: KISEndpoint,
        *,
        name: str | None = None,
        query_params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ):
        name = name or endpoint.name
        logger.info(f"Subscribing to REST endpoint: {name}")
        logger.debug(f"Endpoint: {endpoint.value}, Query params: {query_params}")
        request_spec = get_request_spec(endpoint)

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

    def unsubscribe(self, endpoint: KISEndpoint | str):
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"Unsubscribing from REST endpoint: {name}")
        subscription = self._subscribed.pop(name, None)
        if subscription:
            logger.info(f"Successfully unsubscribed from {name}")
        else:
            logger.debug(f"Subscription {name} not found")


class _KISWebSocketClient:
    def __init__(self, auth: KISAuth, rate_limit_delay):
        logger.info(
            f"Initializing _KISWebSocketClient with rate limit delay: {rate_limit_delay}s"
        )
        self.auth = auth
        self._uri = auth.get_ws_base_url()
        logger.debug(f"WebSocket URI: {self._uri}")
        self._connection: ClientConnection | None = None
        self._subscribed: list[KISEndpoint] = []
        self.msg_queue = []  # ??? something like this maybe?

    def subscribe(self, endpoint):
        raise NotImplementedError("WebSocket client not yet implemented")

        logger.info(f"Subscribing to WebSocket endpoint: {endpoint.name}")
        if len(self._subscribed) == 40:
            err_msg = (
                f"Max 40 WebSocket subscriptions reached, cannot add {endpoint.name}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)
        logger.debug(f"Current WebSocket subscriptions: {len(self._subscribed)}/40")

    def unsubscribe(self, endpoint: KISEndpoint):
        logger.info(f"Unsubscribing from WebSocket endpoint: {endpoint.name}")
        # generate unsubscription message and send to ws
        pass


# TODO: this can be renamed to be general, not just KIS
class KISClient:
    def __init__(self, auth: KISAuth, rest_refresh_rate: int | float = 60):
        logger.info(
            f"Initializing KISClient with REST refresh rate: {rest_refresh_rate}s"
        )
        self.auth = auth
        self.rest_client = _KISRestClient(auth, rest_refresh_rate)
        self.ws_client = _KISWebSocketClient(auth, rate_limit_delay=1)
        self._subscribed: dict[str, Subscription] = {}
        self._subscribed |= self.rest_client._subscribed

    def subscribe(self, endpoint: KISEndpoint, **kwargs):
        logger.debug(f"KISClient.subscribe: {endpoint.name} via {endpoint.method.name}")
        if endpoint.method == Method.GET:
            return self.rest_client.subscribe(endpoint, **kwargs)
        elif endpoint.method == Method.WEBSOCKET:
            return self.ws_client.subscribe(endpoint)
        else:
            err_msg = (
                f"Unsupported method {endpoint.method.name!r} for endpoint {endpoint}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

    def unsubscribe(self, endpoint: KISEndpoint | str):
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"KISClient.unsubscribe: {name}")
        pass

    def start(self):
        logger.info("Starting KISClient")
        pass

    def execute_all_rest(self) -> dict[str, RestResponse | None]:
        return self.rest_client.execute_all()

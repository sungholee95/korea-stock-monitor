from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypedDict

import requests

from .endpoints import Method, RestEndpointSpec, get_endpoint_spec

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from .auth import KISAuth
    from .endpoints import EndpointSpec, KISEndpoint


class RestArgs(TypedDict):
    method: str
    url: str
    headers: dict[str, str]
    params: dict[str, str]


class Subscription:
    def __init__(
        self,
        endpoint_spec: EndpointSpec,
        auth: KISAuth,
        *,
        extra_headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> None:
        if endpoint_spec.method not in (Method.GET, Method.WEBSOCKET):
            # TODO: unsure if this is true?
            raise ValueError("Only GET and WEBSOCKET endpoints can be subscribed to")
        logger.debug(
            f"Constructing `Subscription` for endpoint: {endpoint_spec.tr_id!r}"
        )

        self.endpoint_spec = endpoint_spec
        self.auth = auth
        self.query_params = query_params or {}
        self.extra_headers = extra_headers or {}
        # TODO: need a way to invalidate this cache if auth changes,
        #  or endpoint returns valid tr_cont
        self._cached_rest_args: RestArgs | None = None

    def build_rest_request(
        self,
        extra_headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> RestArgs:
        if not isinstance(self.endpoint_spec, RestEndpointSpec):
            raise TypeError("build_rest_request is only valid for REST endpoint specs")

        logger.debug(f"Building REST request for endpoint: {self.endpoint_spec.tr_id}")
        rest_spec = self.endpoint_spec
        extra_headers = extra_headers or {}
        query_params = query_params or {}
        required_headers = rest_spec.required_headers
        required_query_params = rest_spec.required_query_params

        # Check for unexpected keys (catches wrong endpoint params)
        unused_headers = set(extra_headers.keys()) - required_headers
        if unused_headers:
            err_msg = f"Unexpected header params for this endpoint: {unused_headers}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        unused_query = set(query_params.keys()) - required_query_params
        if unused_query:
            err_msg = f"Unexpected query params for this endpoint: {unused_query}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        headers = self.auth.get_rest_headers()
        headers["tr_id"] = rest_spec.tr_id
        headers.update(extra_headers)

        missing_headers = [
            key
            for key in required_headers
            if key not in headers or headers[key] in (None, "")
        ]
        if missing_headers:
            err_msg = f"Missing required header params: {missing_headers}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        missing_query = [
            key
            for key in required_query_params
            if key not in query_params or query_params[key] in (None, "")
        ]
        if missing_query:
            err_msg = f"Missing required query params: {missing_query}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        base_url = self.auth.get_rest_base_url()

        # Only include required headers and query params in the final request
        final_headers = {k: headers[k] for k in required_headers}
        final_params = {k: query_params[k] for k in required_query_params}

        rest_args: RestArgs = {
            "method": rest_spec.method.name,
            "url": f"{base_url}{rest_spec.api_path}",
            "headers": final_headers,
            "params": final_params,
        }
        self._cached_rest_args = rest_args
        logger.debug(f"Successfully built REST request for {rest_spec.tr_id}")
        return rest_args

    def execute(self) -> requests.Response:
        logger.debug(f"Executing REST request for endpoint: {self.endpoint_spec.tr_id}")
        rest_args = self.build_rest_request(
            query_params=self.query_params,
            extra_headers=self.extra_headers,
        )
        try:
            response = requests.get(
                url=rest_args["url"],
                headers=rest_args["headers"],
                params=rest_args["params"],
                timeout=10,
            )
            logger.debug(f"Received response with status code: {response.status_code}")
            response.raise_for_status()
        except requests.RequestException as e:
            # TODO: better error handling, such as retry logic for transient errors
            err_msg = (
                f"Failed to execute REST request for {self.endpoint_spec.tr_id}: {e}"
            )
            logger.exception(err_msg)
            raise

        # TODO: implement pagination
        # fmt: off
        if (
                response.status_code == 200 and 
                response.headers.get("tr_cont", "") in ["M", "F"]
        ):
            pass
        # fmt: on
        return response


class _KISRestClient:
    def __init__(self, auth: KISAuth, refresh_rate: int | float):
        logger.info(f"Initializing _KISRestClient with refresh rate: {refresh_rate} s")
        self.auth = auth
        self.refresh_rate = refresh_rate
        self._subscribed: dict[str, Subscription] = {}

    async def refresh(self) -> dict[str, requests.Response | None]:
        await asyncio.sleep(self.refresh_rate)
        return self.refresh_all()

    def refresh_all(self) -> dict[str, requests.Response | None]:
        responses: dict[str, requests.Response | None] = {}
        for name, subscription in self._subscribed.items():
            try:
                resp = subscription.execute()
                if resp.status_code == 200:
                    responses[name] = resp
                    logger.debug(f"Successfully refreshed subscription: {name}")
                else:
                    responses[name] = None
            except requests.RequestException as e:
                logger.error(f"Failed to refresh subscription {name}: {e}")
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
    ) -> Subscription:
        name = name or endpoint.name
        logger.info(f"Subscribing to REST endpoint: {name}")
        logger.debug(f"Endpoint: {endpoint.value}, Query params: {query_params}")
        endpoint_spec = get_endpoint_spec(endpoint)
        if not isinstance(endpoint_spec, RestEndpointSpec):
            err_msg = f"Endpoint is not a REST endpoint: {endpoint}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        subscription = Subscription(
            endpoint_spec,
            self.auth,
            query_params=query_params,
            extra_headers=extra_headers,
        )
        self._subscribed[name] = subscription
        logger.info(f"Successfully subscribed to {name}")
        return subscription

    def unsubscribe(self, endpoint: KISEndpoint | str) -> Subscription | None:
        name = endpoint if isinstance(endpoint, str) else endpoint.name
        logger.info(f"Unsubscribing from REST endpoint: {name}")
        subscription = self._subscribed.pop(name, None)
        if subscription:
            logger.info(f"Successfully unsubscribed from {name}")
        else:
            logger.debug(f"Subscription {name} not found")
        return subscription


class _KISWebSocketClient:
    def __init__(self, auth: KISAuth, rate_limit_delay):
        raise NotImplementedError("WebSocket client not yet implemented")
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

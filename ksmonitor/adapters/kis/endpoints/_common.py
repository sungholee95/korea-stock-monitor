from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import BaseRestRequest


logger = logging.getLogger(__name__)


class Method(Enum):
    GET = auto()
    POST = auto()
    WEBSOCKET = auto()


class KISEndpoint(Enum):
    """KIS API endpoint definitions with metadata.

    Each endpoint member provides:
    - description_ko: Korean description of the endpoint
    - method: HTTP method (GET, POST) or WEBSOCKET
    - tr_id: Transaction ID for the KIS API
    - api_path: REST API path (auto-set to "/tryitout" for WebSocket)

    Validation:
    - WebSocket: api_path must not be provided (auto-set)
    - REST: api_path is required

    Access Methods:
    - via name: KISEndpoint.VOLUME_RANK_REST
    - via tr_id (value): KISEndpoint("FHPST01710000")

    """

    description_ko: str
    method: Method
    tr_id: str
    api_path: str

    def __new__(
        cls,
        description_ko: str,
        method: Method,
        tr_id: str,
        api_path: str | None = None,
    ):
        obj = object.__new__(cls)
        if method == Method.WEBSOCKET:
            if api_path is not None:
                raise ValueError(
                    "`api_path` should not be provided for a WebSocket connection; "
                    'It is always "/tryitout"'
                )
            api_path = "/tryitout"
        else:
            if api_path is None:
                raise ValueError("`api_path` is required for REST APIs")

        if "/" in tr_id:
            err = f"Invalid tr_id {tr_id!r}. Could it be `api_path` instead?"
            raise ValueError(err)

        obj._value_ = tr_id
        obj.description_ko = description_ko
        obj.method = method
        obj.tr_id = tr_id
        obj.api_path = api_path
        return obj

    VOLUME_RANK_REST = (
        "거래량순위[v1_국내주식-047]",
        Method.GET,
        "FHPST01710000",
        "/uapi/domestic-stock/v1/quotations/volume-rank",
    )

    INQUIRE_PRICE_REST = (
        "주식현재가 시세[v1_국내주식-008]",
        Method.GET,
        "FHKST01010100",
        "/uapi/domestic-stock/v1/quotations/inquire-price",
    )

    EXECUTED_PRICE_KRX_WS = (
        "국내주식 실시간체결가(KRX) [실시간-003]",
        Method.WEBSOCKET,
        "H0STCNT0",
    )

    ASK_PRICE_KRX_WS = (
        "국내주식 실시간호가 (KRX) [실시간-004]",
        Method.WEBSOCKET,
        "H0STASP0",
    )


# These get populated dynamically by the endpoint modules
#  when their request/response classes are defined
REQUEST_REGISTRY: dict[KISEndpoint, type[BaseRestRequest]] = {}


def get_request_spec(endpoint: KISEndpoint) -> type[BaseRestRequest]:
    try:
        return REQUEST_REGISTRY[endpoint]
    except KeyError:
        err = f"No request class registered for endpoint {endpoint.tr_id!r} ({endpoint.description_ko})"
        logger.error(err)
        raise

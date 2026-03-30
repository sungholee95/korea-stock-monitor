from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..._base.endpoints import Endpoint, Method

if TYPE_CHECKING:
    from ._base import KISBaseRestRequest


logger = logging.getLogger(__name__)


class KISEndpoint(Endpoint):
    """KIS API endpoint definitions with metadata.

    Each endpoint member provides:
    - description_ko: Korean description of the endpoint
    - method: HTTP method (GET, POST) or WEBSOCKET
    - tr_id: Transaction ID
    - api_path: API path (auto-set to "/tryitout" for WebSocket)

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

    def get_request_spec(self) -> type[KISBaseRestRequest]:
        try:
            return REQUEST_REGISTRY[self]
        except KeyError:
            err = f"No request class registered for endpoint {self.tr_id!r} ({self.description_ko})"
            logger.error(err)
            raise


# These get populated dynamically by the endpoint modules
#  when their request/response classes are defined
REQUEST_REGISTRY: dict[KISEndpoint, type[KISBaseRestRequest]] = {}

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from ksmonitor.adapters._shared import Method

if TYPE_CHECKING:
    from ._base import KiwoomBaseRestRequest


logger = logging.getLogger(__name__)


class KiwoomEndpoint(Enum):
    """Kiwoom API endpoint definitions with metadata.

    Each endpoint member provides:
    - description_ko: Korean description of the endpoint
    - method: HTTP method (GET, POST) or WEBSOCKET
    - api_id: Transaction ID
    - api_path: API path

    Validation:
    - WebSocket: api_path must not be provided (auto-set)
    - REST: api_path is required

    Access Methods:
    - via name: KiwoomEndpoint.VOLUME_RANK_REST
    - via api_id (value): KiwoomEndpoint("FHPST01710000")

    """

    description_ko: str
    method: Method
    api_path: str
    api_id: str

    def __new__(
        cls,
        description_ko: str,
        method: Method,
        api_id: str,
        api_path: str | None = None,
    ):
        obj = object.__new__(cls)
        if method == Method.WEBSOCKET:
            raise NotImplementedError()
        else:
            if api_path is None:
                raise ValueError("`api_path` is required for REST APIs")

        if "/" in api_id:
            err = f"Invalid api_id {api_id!r}. Could it be `api_path` instead?"
            raise ValueError(err)

        obj._value_ = api_id
        obj.description_ko = description_ko
        obj.method = method
        obj.api_id = api_id
        obj.api_path = api_path
        return obj

    거래대금상위요청 = (
        "거래대금 상위 종목 요청",
        Method.POST,
        "ka10032",
        "/api/dostk/rkinfo",
    )

    def get_request_spec(self) -> type[KiwoomBaseRestRequest]:
        try:
            return REQUEST_REGISTRY[self]
        except KeyError:
            err = f"No request class registered for endpoint {self.api_id!r} ({self.description_ko})"
            logger.error(err)
            raise


# These get populated dynamically by the endpoint modules
#  when their request/response classes are defined
REQUEST_REGISTRY: dict[KiwoomEndpoint, type[KiwoomBaseRestRequest]] = {}

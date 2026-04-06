from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from ksmonitor.adapters._shared import EndpointError, Method

from ._common import REQUEST_REGISTRY

if TYPE_CHECKING:
    from requests import Response

    from ..auth import KiwoomAuth
    from ._common import KiwoomEndpoint

logger = logging.getLogger(__name__)

type KiwoomRestRequest = KiwoomBaseRestRequest
type KiwoomRestResponse = KiwoomBaseRestResponse
type KiwoomRestResponseOutput = KiwoomBaseRestResponseOutput


@dataclass(repr=False)
class KiwoomBaseRestResponseOutput(ABC):
    """Base class for Kiwoom REST API response outputs.

    Subclasses should define schema fields with metadata
    for Korean descriptions in the following format:

    ```python
    <field_name>: <type> = field(
        default_factory=<type>,
        init=False,
        metadata={"ko": "<응답 Body Element 한글명>"}
    )```
    """

    output_raw: dict[str, str] | list[dict[str, str]]
    polled_at: datetime = field(default_factory=lambda: datetime.now(), init=False)

    @abstractmethod
    def __post_init__(self):
        """Parse raw output into typed fields. Should be implemented by each subclass."""
        raise NotImplementedError()

    @classmethod
    def descriptions_ko(cls) -> dict[str, str]:
        """Return {field_name: korean_description} from field metadata."""
        descriptions = {}

        for f in fields(cls):
            if "ko" in f.metadata:
                descriptions[f.name] = f.metadata["ko"]

        return descriptions

    def build_table(self):
        table = {}
        for f in fields(self):
            if "ko" in f.metadata:
                table[f.metadata["ko"]] = getattr(self, f.name)
        return table


@dataclass(init=False)
class KiwoomBaseRestResponse:
    _endpoint: ClassVar[KiwoomEndpoint]  # Set by each subclass
    _output_schema: ClassVar[type[KiwoomBaseRestResponseOutput]]  # Set by each subclass
    _output_key: str = field(default="output", init=False)

    # headers
    api_id: str
    cont_yn: str
    next_key: str

    # body
    return_code: int  # Result code: 0 = OK, else error
    return_msg: str  # Message 1 (error description)
    output: KiwoomBaseRestResponseOutput

    def __init__(self, response: Response):
        headers = response.headers
        self.api_id: str = headers["api-id"]
        self.cont_yn: str = headers.get("cont-yn", "")
        self.next_key: str = headers.get("next-key", "")

        body = response.json()
        self.return_code: int = body["return_code"]
        self.return_msg: str = body["return_msg"]

        if self.is_ok():
            logger.debug(
                f"Successful response for endpoint "
                f"{self._endpoint.name!r} ({self.api_id!r})"
            )
        else:
            err_msg = (
                f"Received API error (오류코드 {self.return_code!r}: {self.return_msg}) "
                f"for endpoint {self._endpoint.name!r} (api-id={self.api_id!r})"
            )
            logger.error(err_msg)
            raise EndpointError(err_msg)

        output_raw = body[self._output_key]
        self.output = self._output_schema(output_raw)

    def is_ok(self) -> bool:
        return self.return_code == 0

    def has_next_page(self) -> bool:
        return self.cont_yn == "Y"


@dataclass(kw_only=True)
class KiwoomBaseRestRequest(ABC):
    """Base class for Kiwoom REST API requests.

    Subclasses must set `_endpoint` ClassVar to the corresponding `KiwoomEndpoint`.
    `authorization`, `appkey`, `appsecret`, and `content-type` are derived from KiwoomAuth.
    """

    _endpoint: ClassVar[KiwoomEndpoint]  # Set by each subclass
    _response_spec: ClassVar[type[KiwoomBaseRestResponse]]  # Set by each subclass

    auth: KiwoomAuth = field(repr=False)

    cont_yn: str = ""
    next_key: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        REQUEST_REGISTRY[cls._endpoint] = cls

    @property
    def method(self) -> Method:
        """HTTP method from the endpoint definition."""
        return self._endpoint.method

    @property
    def api_path(self) -> str:
        """REST API path from the endpoint definition."""
        return self._endpoint.api_path

    @property
    def description_ko(self) -> str:
        """Korean description from the endpoint definition."""
        return self._endpoint.description_ko

    @property
    def api_id(self) -> str:
        """Transaction ID from the endpoint definition."""
        return self._endpoint.api_id

    def _get_base_headers(self) -> dict[str, str]:
        """Build base headers common to all REST requests."""
        headers = self.auth.get_rest_headers()
        headers["api-id"] = self.api_id

        if self.cont_yn:
            headers["cont-yn"] = self.cont_yn
            headers["next-key"] = self.next_key

        return headers

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        err = (
            "Subclasses should call `super()._base_headers()` "
            "and add any additional headers if needed"
        )
        raise NotImplementedError(err)

    @abstractmethod
    def get_query_params(self) -> dict[str, str]:
        raise NotImplementedError()

    def build_request(
        self, previous_response: KiwoomBaseRestResponse | None = None
    ) -> dict:
        """Build the request payload (headers, query params, body) for this request.
        If `previous_response.has_next_page()`, include pagination headers.
        """

        if previous_response and previous_response.has_next_page():
            self.cont_yn = "Y"
            self.next_key = previous_response.next_key

        return {
            "method": self.method.name,
            "url": f"{self.auth.get_rest_base_url()}{self.api_path}",
            "headers": self.get_headers(),
            "data": json.dumps(self.get_query_params()),
            "timeout": 10,
        }

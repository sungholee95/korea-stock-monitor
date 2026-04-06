from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from ksmonitor.adapters._shared import EndpointError, Method

from ._common import REQUEST_REGISTRY

if TYPE_CHECKING:
    from requests import Response

    from ..auth import KISAuth
    from ._common import KISEndpoint

logger = logging.getLogger(__name__)

type KISRestRequest = KISBaseRestRequest
type KISRestResponse = KISBaseRestResponse
type KISRestResponseOutput = KISBaseRestResponseOutput


@dataclass(repr=False)
class KISBaseRestResponseOutput(ABC):
    """Base class for KIS REST API response outputs.

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

    def _check_keys(self):
        """KIS API responses sometimes have missing or extra keys
        compared to the documented schema. For now, just log any discrepancies.
        """
        actual = (
            self.output_raw.keys()
            if isinstance(self.output_raw, dict)
            else self.output_raw[0].keys()
        )
        expected = {f.name for f in fields(self) if f.metadata.get("ko")}
        unexpected = expected - actual
        missing = actual - expected
        if missing:
            logger.warning(f"Missing keys in schema: {missing}")
        if unexpected:
            logger.warning(f"Unexpected keys in output: {unexpected}")

        return unexpected, missing

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
class KISBaseRestResponse:
    _endpoint: ClassVar[KISEndpoint]  # Set by each subclass
    _output_schema: ClassVar[type[KISBaseRestResponseOutput]]  # Set by each subclass

    # headers
    content_type: str
    tr_id: str
    tr_cont: str

    # body
    rt_cd: str  # Result code: "0" = OK, else error
    msg_cd: str  # Message code (error details)
    msg1: str  # Message 1 (error description)
    output: KISBaseRestResponseOutput

    def __init__(self, response: Response):
        headers = response.headers
        self.content_type: str = headers["content-type"]
        self.tr_id: str = headers["tr_id"]
        self.tr_cont: str = headers.get("tr_cont", "")

        body = response.json()
        self.rt_cd: str = body["rt_cd"]
        self.msg_cd: str = body["msg_cd"]
        self.msg1: str = body["msg1"]

        if self.is_ok():
            logger.debug(
                f"Successful response for endpoint "
                f"{self._endpoint.name!r} ({self.tr_id!r})"
            )
        else:
            err_msg = (
                f"Received KIS API error (오류코드 {self.msg_cd!r}: {self.msg1}) "
                f"for endpoint {self._endpoint.name!r} (tr_id={self.tr_id!r})"
            )
            logger.error(err_msg)
            raise EndpointError(err_msg)

        output_raw = body["output"]
        self.output = self._output_schema(output_raw)

    def is_ok(self) -> bool:
        return self.rt_cd == "0"

    def has_next_page(self) -> bool:
        return self.tr_cont in ("M", "F")


@dataclass(kw_only=True)
class KISBaseRestRequest(ABC):
    """Base class for KIS REST API requests.

    Subclasses must set `_endpoint` ClassVar to the corresponding `KISEndpoint`.
    `authorization`, `appkey`, `appsecret`, and `content-type` are derived from KISAuth.
    """

    _endpoint: ClassVar[KISEndpoint]  # Set by each subclass
    _response_spec: ClassVar[type[KISBaseRestResponse]]  # Set by each subclass

    auth: KISAuth = field(repr=False)

    tr_cont: str | None = None
    custtype: str = "P"

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
    def tr_id(self) -> str:
        """Transaction ID from the endpoint definition."""
        return self._endpoint.tr_id

    def _get_base_headers(self) -> dict[str, str]:
        """Build base headers common to all REST requests."""
        headers = self.auth.get_rest_headers()
        headers |= {
            "tr_id": self.tr_id,
            "custtype": self.custtype,
        }
        if self.tr_cont is not None:
            headers["tr_cont"] = self.tr_cont

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

    def build_request(self) -> dict:
        if self.method == Method.GET:
            return {
                "method": self.method.name,
                "url": f"{self.auth.get_rest_base_url()}{self.api_path}",
                "headers": self.get_headers(),
                "params": self.get_query_params(),
                "timeout": 10,
            }
        elif self.method == Method.POST:
            raise NotImplementedError()
        else:
            raise ValueError(f"Unsupported HTTP method: {self.method}")

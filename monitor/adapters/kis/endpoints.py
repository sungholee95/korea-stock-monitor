import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

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

    def __new__(cls, description_ko, method, tr_id, api_path=None):
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

    EXECUTED_PRICE_KRX_WS = (
        "국내주식 실시간체결가(KRX) [실시간-003]",
        Method.WEBSOCKET,
        "H0STCNT0",
    )

    # Real-time ask;
    ASK_PRICE_KRX_WS = (
        "국내주식 실시간호가 (KRX) [실시간-004]",
        Method.WEBSOCKET,
        "H0STASP0",
    )

    INQUIRE_INVESTOR_TIME_MARKET_REST = (
        "시장별 투자자매매동향(시세)[v1_국내주식-074]",
        Method.GET,
        "FHPTJ04030000",
        "/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market",
    )


_ENDPOINT_NAMES_KO = {
    "거래량 순위": KISEndpoint.VOLUME_RANK_REST,
    "실시간 체결가 (KRX)": KISEndpoint.EXECUTED_PRICE_KRX_WS,
    "실시간 호가 (KRX)": KISEndpoint.ASK_PRICE_KRX_WS,
    "시장별 투자자매매동향": KISEndpoint.INQUIRE_INVESTOR_TIME_MARKET_REST,
}

ENDPOINT_NAMES = {
    "ko": _ENDPOINT_NAMES_KO,
}


def resolve_endpoint_by_name(name: str, language: str = "ko") -> KISEndpoint:
    if language not in ENDPOINT_NAMES:
        err_msg = f"Language not supported: {language}"
        logger.error(err_msg)
        raise KeyError(err_msg)
    if name not in ENDPOINT_NAMES[language]:
        err_msg = f"Endpoint name not found: {name!r} (language: {language})"
        logger.error(err_msg)
        raise KeyError(err_msg)
    endpoint = ENDPOINT_NAMES[language][name]
    logger.debug(f"Resolved endpoint {name!r} to {endpoint.name}")
    return endpoint


@dataclass
class BaseEndpointSpec(ABC):
    # TODO: add name of endpoint
    method: Method
    description_ko: str
    api_path: str  # eg) "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id: str

    @classmethod
    @abstractmethod
    def _from_endpoint(cls, endpoint: KISEndpoint, **kwargs):
        raise NotImplementedError()


type EndpointSpec = BaseEndpointSpec


@dataclass
class RestEndpointSpec(BaseEndpointSpec):
    required_headers: set[str] = field(default_factory=set)
    required_query_params: set[str] = field(default_factory=set)
    # TODO: optional headers and optional query params

    @classmethod
    def _from_endpoint(cls, endpoint: KISEndpoint, **kwargs):
        if endpoint.method == Method.WEBSOCKET:
            err_msg = f"Endpoint {endpoint} is intended for WebSocket, not REST"
            logger.error(err_msg)
            raise ValueError(err_msg)

        logger.debug(f"Creating RestEndpointSpec from endpoint: {endpoint.name}")

        required_headers = kwargs["required_headers"]
        if not isinstance(required_headers, set):
            err_msg = "`required_headers` must be a set of strings"
            logger.error(err_msg)
            raise TypeError(err_msg)

        required_query_params = kwargs["required_query_params"]
        if not isinstance(required_query_params, set):
            err_msg = "`required_query_params` must be a set of strings"
            logger.error(err_msg)
            raise TypeError(err_msg)

        logger.debug(
            f"Creating RestEndpointSpec with {len(required_headers)} required headers and {len(required_query_params)} required query params"
        )
        return cls(
            description_ko=endpoint.description_ko,
            api_path=endpoint.api_path,
            tr_id=endpoint.tr_id,
            method=endpoint.method,
            required_headers=required_headers,
            required_query_params=required_query_params,
        )


@dataclass
class WebSocketEndpointSpec(BaseEndpointSpec):
    def build(self): ...

    def build_headers(self): ...

    def build_body(self): ...


ENDPOINTSPEC_REGISTRY = {
    KISEndpoint.INQUIRE_INVESTOR_TIME_MARKET_REST: RestEndpointSpec._from_endpoint(
        KISEndpoint.INQUIRE_INVESTOR_TIME_MARKET_REST,
        required_headers={
            "content-type",
            "authorization",
            "appkey",
            "appsecret",
            "tr_id",
            "custtype",
        },
        required_query_params={
            "fid_input_iscd",
            "fid_input_iscd_2",
        },
    )
}


def get_endpoint_spec(endpoint: KISEndpoint) -> EndpointSpec:
    """Get the specs for an endpoint.

    Args:
        endpoint: KISEndpoint enum key

    Returns:
        Corresponding EndpointSpec

    Raises:
        KeyError: If endpoint not registered

    """
    if endpoint not in ENDPOINTSPEC_REGISTRY:
        err_msg = f"Endpoint not registered: {endpoint}"
        logger.error(err_msg)
        raise KeyError(err_msg)
    return ENDPOINTSPEC_REGISTRY[endpoint]

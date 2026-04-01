from enum import Enum, auto


class Method(Enum):
    GET = auto()
    POST = auto()
    WEBSOCKET = auto()


class EndpointError(RuntimeError):
    pass

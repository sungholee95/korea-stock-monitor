from __future__ import annotations

from abc import abstractmethod
from enum import Enum, auto


class Method(Enum):
    GET = auto()
    POST = auto()
    WEBSOCKET = auto()


class EndpointError(RuntimeError):
    pass


class Endpoint(Enum):
    description_ko: str
    method: Method
    api_path: str

    @abstractmethod
    def get_request_spec(self):
        """Return the registered request class for this endpoint."""
        ...

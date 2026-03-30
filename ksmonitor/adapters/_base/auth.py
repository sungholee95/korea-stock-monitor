from __future__ import annotations

from abc import ABC, abstractmethod

from .config import Config


class Auth(ABC):
    is_paper: bool
    config: Config

    @abstractmethod
    def get_rest_base_url(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_ws_base_url(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_access_token(self):
        raise NotImplementedError()

    @abstractmethod
    def get_rest_headers(self) -> dict[str, str]:
        raise NotImplementedError()

    @abstractmethod
    def get_ws_headers(self) -> dict[str, str]:
        raise NotImplementedError()

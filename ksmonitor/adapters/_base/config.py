from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Config(ABC):
    is_paper: bool

    # required if not is_paper
    my_app_key_name: str | None = None
    my_app_sec_name: str | None = None
    my_acct_stock: str | None = None
    my_acct_future: str | None = None

    # required if is_paper
    my_paper_app_key_name: str | None = None
    my_paper_app_sec_name: str | None = None
    my_paper_stock: str | None = None
    my_paper_future: str | None = None

    url_prod: str
    url_paper: str
    ws_prod: str
    ws_paper: str

    @classmethod
    @abstractmethod
    def from_yaml(cls, *, yaml_file: Path | None = None, is_paper: bool = False):
        raise NotImplementedError()

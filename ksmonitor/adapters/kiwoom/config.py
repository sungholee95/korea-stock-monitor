from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from .._base.config import Config

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("~").expanduser() / ".ksmonitor" / "config" / "kiwoom.yaml"


@dataclass(kw_only=True)
class KiwoomConfig(Config):
    # paper (모의) mode
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

    url_prod = "https://api.kiwoom.com"
    url_paper = "https://mockapi.kiwoom.com"
    ws_prod = "wss://api.kiwoom.com:10000"
    ws_paper = "wss://mockapi.kiwoom.com:10000"

    @classmethod
    def from_yaml(
        cls, *, yaml_file: Path = _DEFAULT_CONFIG_PATH, is_paper: bool = False
    ) -> KiwoomConfig:
        logger.info("Loading Kiwoom configuration from: %s...", yaml_file)
        if not is_paper:
            logger.info("Running in prod mode")
        else:
            logger.info("Running in paper mode")

        if not Path(yaml_file).is_file():
            err = f"Config file ('{yaml_file}') not found"
            logger.error(err)
            raise FileNotFoundError(err)

        with open(yaml_file, encoding="UTF-8") as f:
            cfg = yaml.load(f, Loader=yaml.SafeLoader)

        if not cfg:
            err = f"Config file ({yaml_file}) is empty"
            logger.error(err)
            raise ValueError(err)

        if not is_paper:
            required_keys = [
                "my_app_key_name",
                "my_app_sec_name",
                "my_acct_stock",
                "my_acct_future",
            ]
        else:
            required_keys = [
                "my_paper_app_key_name",
                "my_paper_app_sec_name",
                "my_paper_stock",
                "my_paper_future",
            ]

        # Only let allowed keys to be used to prevent eg. API urls from being hijacked
        allowed_keys = [
            "my_app_key_name",
            "my_app_sec_name",
            "my_acct_stock",
            "my_acct_future",
            "my_paper_app_key_name",
            "my_paper_app_sec_name",
            "my_paper_stock",
            "my_paper_future",
        ]

        missing_keys = [k for k in required_keys if k not in cfg]
        if missing_keys:
            err = f"Missing required config keys: {missing_keys}"
            logger.error(err)
            raise ValueError(err)

        disallowed_keys = [k for k in cfg if k not in allowed_keys]
        if disallowed_keys:
            err = f"Found illegal config keys: {disallowed_keys}"
            logger.error(err)
            raise ValueError(err)

        logger.debug("Config loaded successfully from %s", yaml_file)
        return cls(**cfg | {"is_paper": is_paper})

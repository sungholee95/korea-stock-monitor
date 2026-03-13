import logging
import os
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class KISConfig:
    is_paper: bool

    my_htsid: str

    my_app_key_name: str
    my_app_sec_name: str
    my_acct_stock: str
    my_acct_future: str
    my_prod: str

    my_paper_app_key_name: str | None = None
    my_paper_app_sec_name: str | None = None
    my_paper_stock: str | None = None
    my_paper_future: str | None = None

    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    url_prod = "https://openapi.koreainvestment.com:9443"
    url_paper = "https://openapivts.koreainvestment.com:29443"
    ws_prod = "wss://ops.koreainvestment.com:21000"
    ws_paper = "wss://ops.koreainvestment.com:31000"

    @classmethod
    def from_yaml(cls, is_paper: bool, yaml_file=None) -> "KISConfig":
        if yaml_file is None:
            yaml_file = os.path.join(
                os.path.expanduser("~"), "KIS", "config", "config.yaml"
            )

        logger.info(f"Loading KIS configuration from: {yaml_file}...")
        if not is_paper:
            logger.info("Running in prod mode")
        else:
            logger.info("Running in paper mode")

        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"Config file ({yaml_file}) not found")

        with open(yaml_file, encoding="UTF-8") as f:
            cfg = yaml.load(f, Loader=yaml.SafeLoader)

        if not cfg:
            raise ValueError(f"Config file ({yaml_file}) is empty")

        if not is_paper:
            required_keys = [
                "my_htsid",
                "my_app_key_name",
                "my_app_sec_name",
                "my_acct_stock",
                "my_acct_future",
                "my_prod",
            ]
        else:
            required_keys = [
                "my_htsid",
                "my_paper_app_key_name",
                "my_paper_app_sec_name",
                "my_paper_stock",
                "my_paper_future",
                "my_prod",
            ]

        # Only let allowed keys to be used to prevent eg. API urls from being hijacked
        allowed_keys = [
            "my_htsid",
            "my_app_key_name",
            "my_app_sec_name",
            "my_acct_stock",
            "my_acct_future",
            "my_paper_app_key_name",
            "my_paper_app_sec_name",
            "my_paper_stock",
            "my_paper_future",
            "my_prod",
            "user_agent",
        ]

        missing_keys = [k for k in required_keys if k not in cfg]
        if missing_keys:
            raise ValueError(f"Missing required config keys: {missing_keys}")

        disallowed_keys = [k for k in cfg if k not in allowed_keys]
        if disallowed_keys:
            raise ValueError(f"Found illegal config keys: {disallowed_keys}")

        logger.debug(f"Config loaded successfully from {yaml_file}")
        return cls(**cfg | {"is_paper": is_paper})

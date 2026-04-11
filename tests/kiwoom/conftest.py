from unittest.mock import MagicMock

import pytest

from ksmonitor.adapters.kiwoom.auth import KiwoomAuth
from ksmonitor.adapters.kiwoom.config import KiwoomConfig


@pytest.fixture
def kiwoom_prod_config() -> KiwoomConfig:
    return KiwoomConfig(
        is_paper=False,
        my_app_key_name="prod_app",
        my_app_sec_name="prod_sec",
        my_acct_stock="12345678",
        my_acct_future="87654321",
    )


@pytest.fixture
def kiwoom_paper_config() -> KiwoomConfig:
    return KiwoomConfig(
        is_paper=True,
        my_paper_app_key_name="paper_app",
        my_paper_app_sec_name="paper_sec",
        my_paper_stock="11111111",
        my_paper_future="22222222",
    )


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Remove requests.sessions.Session.request for all tests."""
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture
def mock_auth(kiwoom_prod_config: KiwoomConfig):
    auth = MagicMock(spec=KiwoomAuth)
    auth.config = kiwoom_prod_config
    auth.get_rest_headers.return_value = {
        "authorization": "Bearer fake_token",
        "Content-Type": "application/json;charset=UTF-8",
    }
    return auth


@pytest.fixture
def mock_paper_auth(kiwoom_paper_config: KiwoomConfig):
    auth = MagicMock(spec=KiwoomAuth)
    auth.config = kiwoom_paper_config
    auth.get_rest_headers.return_value = {
        "authorization": "Bearer fake_token",
        "Content-Type": "application/json;charset=UTF-8",
    }
    return auth

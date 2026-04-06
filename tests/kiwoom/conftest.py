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


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Remove requests.sessions.Session.request for all tests."""
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture
def mock_auth(kiwoom_prod_config: KiwoomConfig):
    auth = MagicMock(spec=KiwoomAuth)
    auth.get_rest_headers.return_value = {
        "authorization": "Bearer fake_token",
        "Content-Type": "application/json;charset=UTF-8",
    }
    return auth

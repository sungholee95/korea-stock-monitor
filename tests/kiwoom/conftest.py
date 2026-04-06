import pytest

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

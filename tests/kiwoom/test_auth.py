from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from ksmonitor.adapters.kiwoom.auth import AccessToken, KiwoomAuth

if TYPE_CHECKING:
    from ksmonitor.adapters.kiwoom.config import KiwoomConfig


class TestAccessToken:
    def test_token_is_valid(self):
        token = AccessToken(
            access_token="tok",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert token.is_valid()
        assert token.expires_in > 0

    def test_token_is_expired(self):
        token = AccessToken(
            access_token="tok",
            token_type="Bearer",
            expires_at=datetime.now() - timedelta(seconds=1),
        )
        assert not token.is_valid()

    def test_expires_in_computed_from_expires_at(self):
        """expires_in is computed in __post_init__ from expires_at."""

        expires_at = datetime.now() + timedelta(hours=1)
        token = AccessToken(
            access_token="tok",
            token_type="Bearer",
            expires_at=expires_at,
        )
        # 1hr == 3600 seconds but allow some slack for test execution time
        assert 3590 <= token.expires_in <= 3600


class TestKiwoomAuthTokenCaching:
    @patch("ksmonitor.adapters.kiwoom.auth.keyring")
    def test_retrieve_cached_valid_token(
        self, mock_keyring, kiwoom_prod_config: KiwoomConfig
    ):
        """Retrieve valid cached token from keyring"""

        def my_get_password(svc_name, username):
            if username == "access_token":
                return "tok123"
            elif username == "access_token_expires_at":
                # valid for 12 more hours
                return (datetime.now() + timedelta(hours=12)).isoformat()

        mock_keyring.get_password.side_effect = my_get_password
        auth = KiwoomAuth(kiwoom_prod_config)

        token = auth.get_access_token()
        assert token.access_token == "tok123"

    @patch("ksmonitor.adapters.kiwoom.auth.keyring")
    def test_expire_cached_expired_token(self, mock_keyring, kiwoom_prod_config):
        """Expire old (expired) cached token and send a request to acquire a new token"""

        def my_get_password(svc_name, username):
            if username == "access_token":
                return "tok123"
            elif username == "access_token_expires_at":
                # expired 12 hours ago
                return (datetime.now() - timedelta(hours=12)).isoformat()

        mock_keyring.get_password.side_effect = my_get_password
        auth = KiwoomAuth(kiwoom_prod_config)
        with patch.object(auth, "_acquire_access_token") as mock_acquire:
            # check that Auth._acquire_access_token get called
            #  without actually calling the method
            _ = auth.get_access_token()
            mock_acquire.assert_called_once()

    @patch("ksmonitor.adapters.kiwoom.auth.keyring")
    def test_no_exp_time_raises(self, mock_keyring, kiwoom_prod_config):
        """If token exists in keyring but expiration time doesn't, raise exception"""

        def my_get_password(svc_name, username):
            # svc_name is always "kiwoom" in the current module
            #  and remains unused
            if username == "access_token":
                return "tok123"
            elif username == "access_token_expires_at":
                # expired 12 hours ago
                return None

        mock_keyring.get_password.side_effect = my_get_password
        auth = KiwoomAuth(kiwoom_prod_config)
        with pytest.raises(RuntimeError):
            _ = auth.get_access_token()

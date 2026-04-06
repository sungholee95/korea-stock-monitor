import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import keyring
import requests

from .config import KiwoomConfig

logger = logging.getLogger(__name__)


@dataclass
class AccessToken:
    """OAuth access token information."""

    access_token: str
    token_type: str
    expires_at: datetime  # name in response is "expires_dt"
    expires_in: int = field(init=False)

    def __post_init__(self):
        self.expires_in = int((self.expires_at - datetime.now()).total_seconds())

    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at


class KiwoomAuth:
    def __init__(self, config: KiwoomConfig):
        self.config = config
        self.is_paper = config.is_paper

        self._access_token: AccessToken | None = None

        self._rest_headers = {"Content-Type": "application/json;charset=UTF-8"}
        self._websocket_headers = {"Content-Type": "application/json;charset=UTF-8"}

    def _get_credentials(self) -> tuple[str, str]:
        """Retrieve app key and app secret from the Credentials Manager.

        Raises:
            RuntimeError: If either app key or app secret is None (not found in credentials manager)

        """

        if not self.is_paper:
            app_key_name = self.config.my_app_key_name
            app_sec_name = self.config.my_app_sec_name
        else:
            app_key_name = self.config.my_paper_app_key_name
            app_sec_name = self.config.my_paper_app_sec_name

        logger.debug(
            f"Retrieving credentials from keyring: kiwoom@{app_key_name}, {app_sec_name}"
        )

        app_key = keyring.get_password("kiwoom", app_key_name)  # pyright: ignore[reportArgumentType]
        app_sec = keyring.get_password("kiwoom", app_sec_name)  # pyright: ignore[reportArgumentType]

        if not (app_key and app_sec):
            err_msg = (
                f"App credentials not found in credentials manager. "
                f"Expected keys: {app_key_name!r}, {app_sec_name!r} in service 'kiwoom'"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        return app_key, app_sec

    def _acquire_access_token(self) -> AccessToken:
        logger.info("Acquiring new access token")

        url = f"{self.get_rest_base_url()}/oauth2/token"
        app_key, app_sec = self._get_credentials()
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_sec,
        }
        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers=self._rest_headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            err_msg = f"Failed to acquire OAuth access token: {e}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from e

        expires_at = datetime.strptime(data["expires_dt"], "%Y%m%d%H%M%S")

        token = AccessToken(
            access_token=data["token"],
            token_type=data["token_type"],
            expires_at=expires_at,
        )

        # save token in keyring
        keyring.set_password("kiwoom", "access_token", token.access_token)
        keyring.set_password(
            "kiwoom",
            "access_token_expires_at",
            token.expires_at.isoformat(),
        )
        logger.debug("Successfully acquired new OAuth access token")

        return token

    def get_rest_base_url(self) -> str:
        """Get API base URL for the current environment."""
        return self.config.url_prod if not self.is_paper else self.config.url_paper

    def get_ws_base_url(self) -> str:
        """Get WebSocket base URL for the current environment."""
        return self.config.ws_prod if not self.is_paper else self.config.ws_paper

    def get_access_token(self) -> AccessToken:
        # Return cached token if valid
        if self._access_token and self._access_token.is_valid():
            return self._access_token

        # Return saved token from credentials manger, if still valid
        saved_token = keyring.get_password("kiwoom", "access_token")
        if saved_token is not None:
            exp_time_str = keyring.get_password("kiwoom", "access_token_expires_at")
            if exp_time_str is None:
                # if this raises, something went wrong during caching,
                #  and only the token was saved.
                # Invalidate the token manually and reacquire
                err = (
                    "`access_token_expires_at` should exist in credentials if "
                    "`access_token` is saved but is None"
                )
                logger.critical(err)
                raise RuntimeError(err)

            expires_at = datetime.fromisoformat(exp_time_str)
            if datetime.now() < expires_at:
                logger.info(
                    f"Using saved token from keyring (expires at: {expires_at})"
                )
                self._access_token = AccessToken(
                    access_token=saved_token,
                    token_type="Bearer",
                    expires_at=expires_at,
                )
                return self._access_token
            else:
                logger.debug("Saved token expired. Deleting saved token")
                keyring.delete_password("kiwoom", "access_token")
                keyring.delete_password("kiwoom", "access_token_expires_at")

        # Acquire new token
        token = self._acquire_access_token()
        self._access_token = token
        return self._access_token

    def get_rest_headers(self) -> dict[str, str]:
        """Get headers for REST, including authorization

        Returns:
            Dictionary of headers with authorization

        """

        headers = self._rest_headers.copy()
        token = self.get_access_token()
        headers["authorization"] = f"{token.token_type} {token.access_token}"
        return headers

    def get_ws_headers(self) -> dict[str, str]:
        """Get headers for WebSocket connection, including authorization

        Returns:
            Dictionary of headers with approval key

        """

        headers = self._websocket_headers.copy()
        headers["approval_key"] = self.get_access_token().access_token
        return headers

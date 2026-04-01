import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import keyring
import requests

from .config import KISConfig

logger = logging.getLogger(__name__)


@dataclass
class AccessToken:
    """OAuth access token information."""

    access_token: str
    token_type: str
    expires_in: int
    expires_at: datetime  # name in response is "access_token_token_expired"

    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at


@dataclass
class WSApprovalKey:
    """WebSocket approval key."""

    key: str
    issued_at: datetime
    expires_at: datetime = field(init=False)

    def __post_init__(self):
        # expiration date not given by API, so we calculate it
        self.expires_at = self.issued_at + timedelta(days=1)

    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at


class KISAuth:
    def __init__(self, config: KISConfig):
        self.config = config
        self.is_paper = config.is_paper

        self._access_token: AccessToken | None = None
        self._ws_approval_key: WSApprovalKey | None = None

        self._rest_headers = {
            "content-type": "application/json; charset=utf-8",
        }
        self._websocket_headers = {
            "content-type": "utf-8",
        }

    def _get_credentials(self) -> tuple[str, str]:
        """Retreive app key and app secret from the Credentials Manager.

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
            f"Retrieving credentials from keyring: kis@{app_key_name}, {app_sec_name}"
        )

        app_key = keyring.get_password("kis", app_key_name)  # pyright: ignore[reportArgumentType]
        app_sec = keyring.get_password("kis", app_sec_name)  # pyright: ignore[reportArgumentType]

        if not (app_key and app_sec):
            err_msg = (
                f"App credentials not found in credentials manager. "
                f"Expected keys: {app_key_name!r}, {app_sec_name!r} in service 'kis'"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        return app_key, app_sec

    def _acquire_access_token(self) -> AccessToken:
        logger.info("Acquiring new access token")

        url = f"{self.get_rest_base_url()}/oauth2/tokenP"
        app_key, app_sec = self._get_credentials()
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_sec,
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

        expires_at = datetime.strptime(
            data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S"
        )

        token = AccessToken(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            expires_at=expires_at,
        )

        # save token in keyring
        keyring.set_password("kis", "access_token", token.access_token)
        keyring.set_password(
            "kis",
            "access_token_expires_at",
            token.expires_at.isoformat(),
        )
        logger.debug("Successfully acquired new OAuth access token")

        return token

    def _acquire_ws_approval_key(self) -> WSApprovalKey:
        logger.info("Acquiring new WebSocket approval key")

        url = f"{self.get_rest_base_url()}/oauth2/Approval"
        app_key, app_sec = self._get_credentials()
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_sec,
        }
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers=self._rest_headers,
            timeout=10,
        )
        data = response.json()
        issued_at = datetime.now()

        if response.status_code != 200:
            err_msg = (
                f"Approval key acquisition failed: {data.get('msg1', 'Unknown error')}"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        approval_key = WSApprovalKey(
            key=data["approval_key"],
            issued_at=issued_at,
        )

        keyring.set_password("kis", "ws_approval_key", approval_key.key)
        keyring.set_password(
            "kis",
            "ws_approval_key_expires_at",
            approval_key.expires_at.isoformat(),
        )
        logger.debug("Successfully acquired new WebSocket approval key")

        return approval_key

    def get_rest_base_url(self) -> str:
        """Get API base URL for the current environment."""
        return self.config.url_prod if not self.is_paper else self.config.url_paper

    def get_ws_base_url(self) -> str:
        """Get WebSocket base URL for the current environment."""
        return self.config.ws_prod if not self.is_paper else self.config.ws_paper

    def get_access_token(self) -> AccessToken:
        # Return cached token if valid
        if self._access_token and self._access_token.is_valid():
            logger.info("Using cached token issued")
            return self._access_token

        # Return saved token from credentials manger, if still valid
        saved_token = keyring.get_password("kis", "access_token")
        if saved_token is not None:
            exp_time_str = keyring.get_password("kis", "access_token_expires_at")
            if exp_time_str is None:
                raise RuntimeError(
                    "`access_token_expires_at` should exist in credentials if "
                    "`access_token` is saved but is None"
                )
            expires_at = datetime.fromisoformat(exp_time_str)
            if datetime.now() < expires_at:
                logger.info(
                    f"Using saved token from keyring (expires at: {expires_at})"
                )
                self._access_token = AccessToken(
                    access_token=saved_token,
                    token_type="Bearer",
                    expires_in=int((expires_at - datetime.now()).total_seconds()),
                    expires_at=expires_at,
                )
                return self._access_token
            else:
                logger.debug("Saved token expired. Deleting saved token")
                keyring.delete_password("kis", "access_token")
                keyring.delete_password("kis", "access_token_expires_at")

        # Acquire new token
        token = self._acquire_access_token()
        self._access_token = token
        return self._access_token

    def get_ws_approval_key(self) -> WSApprovalKey:
        # Return cached key if valid
        if self._ws_approval_key and self._ws_approval_key.is_valid():
            logger.debug("Using cached WebSocket approval key")
            return self._ws_approval_key

        # Return saved approval key from credentials manger, if still valid
        saved_key = keyring.get_password("kis", "ws_approval_key")
        if saved_key is not None:
            exp_time_str = keyring.get_password("kis", "ws_approval_key_expires_at")
            if exp_time_str is None:
                raise RuntimeError(
                    "`ws_approval_key_expires_at` should exist in credentials if "
                    "`ws_approval_key` is saved but is None"
                )
            expires_at = datetime.fromisoformat(exp_time_str)
            if datetime.now() < expires_at:
                logger.info(
                    f"Using saved approval key from keyring (expires at: {expires_at})"
                )
                self._ws_approval_key = WSApprovalKey(
                    saved_key,
                    issued_at=expires_at - timedelta(days=1),
                )
                return self._ws_approval_key
            else:
                logger.debug("Saved key expired. Deleting saved key")
                keyring.delete_password("kis", "ws_approval_key")
                keyring.delete_password("kis", "ws_approval_key_expires_at")

        # Acquire new key
        approval_key = self._acquire_ws_approval_key()
        self._ws_approval_key = approval_key
        return self._ws_approval_key

    def get_rest_headers(self) -> dict[str, str]:
        """Get headers for REST, including authorization

        Returns:
            Dictionary of headers with authorization

        """
        appkey, appsec = self._get_credentials()
        headers = self._rest_headers.copy()
        token = self.get_access_token()
        headers["authorization"] = f"{token.token_type} {token.access_token}"
        headers["appkey"] = appkey
        headers["appsecret"] = appsec
        return headers

    def get_ws_headers(self) -> dict[str, str]:
        """Get headers for WebSocket connection, including authorization

        Returns:
            Dictionary of headers with approval key

        """
        headers = self._websocket_headers.copy()
        headers["approval_key"] = self.get_ws_approval_key().key
        return headers

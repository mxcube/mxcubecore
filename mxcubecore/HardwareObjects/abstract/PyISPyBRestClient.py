import logging
from datetime import datetime, timedelta, timezone
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

from requests import Session

log = logging.getLogger("py-ispyb_client")


class NoTokenException(Exception):
    """Exception raised when no token is returned from authentication."""


class PyISPyBUnsuccessfulResponse(Exception):
    """Exception raised when a response from the server is unsuccessful (not 200)."""


class AuthenticationExpired(Exception):
    """Raised when authentication refresh failed."""


class PyISPyBRestClient:
    """REST client for PyISPyB.

    It handles authentication and communication with PyISPyB REST API.
    """

    REFRESH_MARGIN_SECONDS = 60

    def __init__(self, rest_root: str, timeout: int = 5):
        self._rest_root = rest_root
        self._session = Session()
        self._timeout = timeout
        self._username = None
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None

    def authenticate(self, user_name: str, token: str):
        self._username = user_name
        response = self.post(
            "auth/login",
            json={
                "plugin": "keycloak",
                "login": user_name,
                "token": token,
            },
            skip_refresh=True,
        )
        self._store_tokens(response)

    def post(self, endpoint, **kwargs):
        return self._request(self._session.post, endpoint, **kwargs)

    def get(self, endpoint, **kwargs):
        return self._request(self._session.get, endpoint, **kwargs)

    def patch(self, endpoint, **kwargs):
        return self._request(self._session.patch, endpoint, **kwargs)

    def update_proxies(self, proxy: dict):
        self._session.proxies.update(proxy)

    def _request(self, method, endpoint, skip_refresh=False, **kwargs):  # noqa: FBT002
        if not skip_refresh and self._is_token_expired():
            self._refresh_access_token()
        timeout = kwargs.pop("timeout", self._timeout)
        url = urljoin(self._rest_root, endpoint)
        response = method(url, timeout=timeout, **kwargs)
        if response.status_code == 401 and not skip_refresh:
            log.warning("Received 401. Attempting token refresh.")
            self._refresh_access_token()
            response = method(url, timeout=timeout, **kwargs)
        return self.decode_json_response(response)

    def _refresh_access_token(self):
        if not self._refresh_token:
            msg = "No refresh token available"
            raise AuthenticationExpired(msg)
        log.info("Refreshing keycloak access token")
        url = urljoin(self._rest_root, "auth/refresh")
        response = self._session.post(
            url,
            timeout=self._timeout,
            json={"refreshToken": self._refresh_token},
        )
        if response.status_code != 200:
            msg = "Failed to refresh token"
            raise AuthenticationExpired(msg)
        try:
            self._store_tokens(response.json())
        except JSONDecodeError as ex:
            msg = "Authentication response malformed."
            log.exception(msg)
            raise AuthenticationExpired(msg) from ex

    @staticmethod
    def decode_json_response(response):
        log.debug(
            "Received response from %s. Status code: %s, Response text: %s",
            response.url,
            response.status_code,
            response.text,
        )
        if response.status_code not in (200, 201):
            msg = (
                f"Request to {response.url} failed with code: {response.status_code}. "
                f"Response: {response.text}"
            )
            raise PyISPyBUnsuccessfulResponse(msg)
        try:
            response_json = response.json()
        except JSONDecodeError:
            log.exception(
                "Failed to decode JSON response from %s. "
                "Status code: %s, Response text: %s",
                response.url,
                response.status_code,
                response.text,
            )
            raise
        if "results" in response_json:
            return response_json["results"]
        return response_json

    def _store_tokens(self, response: dict):
        if not isinstance(response, dict):
            msg = (
                "Authentication response malformed: expected dict, "
                f"got {type(response)}"
            )
            raise NoTokenException(msg)
        access_token = response.get("token")
        refresh_token = response.get("refreshToken")
        expires_in = response.get("expiresIn", 300)
        if not access_token:
            msg = "Authentication failed. No access token received."
            raise NoTokenException(msg)
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._set_authorization_header(access_token)

    def _is_token_expired(self) -> bool:
        if self._token_expiry is None:
            return True

        return datetime.now(timezone.utc) >= (
            self._token_expiry - timedelta(seconds=self.REFRESH_MARGIN_SECONDS)
        )

    def _set_authorization_header(self, token: str):
        self._session.headers.update({"Authorization": f"Bearer {token}"})

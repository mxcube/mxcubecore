# ruff: noqa: TD003, FIX002, ERA001
import logging
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

from requests import Session

log = logging.getLogger("py-ispyb_client")


class NoTokenException(Exception):
    """Exception raised when no token is returned from authentication."""


class PyISPyBUnsuccessfulResponse(Exception):
    """Exception raised when a response from the server is unsuccessful (not 200)."""


class PyISPyBRestClient:
    """REST client for PyISPyB.

    It handles authentication and communication with PyISPyB REST API.
    """

    def __init__(self, rest_root: str, timeout: int = 5):
        self._rest_root = rest_root
        self._session = Session()
        self._timeout = timeout

    def _decode_json_response(self, response):
        log.info(  # TODO@dominikatrojanowska: change to debug
            "Received response from %s. Status code: %s, Response text: %s",
            response.url,
            response.status_code,
            response.text,
        )
        if response.status_code not in (200, 201):
            msg = (
                f"Request to {response.url} failed with code: {response.status_code} "
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

    def post(self, endpoint, **kwargs):
        timeout = kwargs.pop("timeout", self._timeout)
        url = urljoin(self._rest_root, endpoint)
        log.info(  # TODO@dominikatrojanowska: chnage to debug
            f"POST request to {url} with timeout {timeout} and kwargs {kwargs}"
        )
        return self._decode_json_response(
            self._session.post(url, timeout=timeout, **kwargs)
        )

    def get(self, endpoint, **kwargs):
        timeout = kwargs.pop("timeout", self._timeout)
        url = urljoin(self._rest_root, endpoint)
        log.info(  # TODO@dominikatrojanowska: change to debug
            f"GET request to {url} with timeout {timeout} and kwargs {kwargs}"
        )
        return self._decode_json_response(
            self._session.get(url, timeout=timeout, **kwargs)
        )

    def _get_auth_token(self, response) -> str:
        token = None
        try:
            token = response.get("token", None)
        except Exception:
            log.exception(
                "Authentication failed. Status code: %s, Response: %s",
                response.status_code,
                response.text,
            )
        if token is None:
            err = "Authentication failed. No token received."
            raise NoTokenException(err)
        return token

    def authenticate(self, user_name: str, token: str):
        response = self.post(
            "auth/login",
            json={
                "plugin": "keycloak",
                "login": user_name,
                "token": token,
            },
        )
        token = self._get_auth_token(response)
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        # TODO@dominikatrojanowska: get refresh token and implement
        # token refresh mechanism when it will be provided by py-ipsyb

    def update_proxies(self, proxy: dict):
        self._session.proxies.update(proxy)

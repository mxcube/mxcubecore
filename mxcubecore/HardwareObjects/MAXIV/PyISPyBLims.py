# ruff: noqa: TD003, FIX002, ERA001
import logging
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

import requests

log = logging.getLogger("py-ispyb_client")


class NoTokenException(Exception):
    """Exception raised when no token is returned from authentication."""


class PyISPyBRestClient:
    """REST client for PyISPyB.

    It handles authentication and communication with PyISPyB REST API.
    """

    def __init__(self, rest_root: str):
        self._rest_root = rest_root
        self._session = requests.Session()

    def _decode_json_response(self, response):
        log.info(  # TODO@dominikatrojanowska: remove
            "Received response from %s. Status code: %s, Response text: %s",
            response.url,
            response.status_code,
            response.text,
        )
        try:
            return response.json()
        except JSONDecodeError:
            log.exception(
                "Failed to decode JSON response from %s. "
                "Status code: %s, Response text: %s",
                response.url,
                response.status_code,
                response.text,
            )
            raise

    def post(self, endpoint, timeout=5, **kwargs):
        url = urljoin(self._rest_root, endpoint)
        log.info(  # TODO@dominikatrojanowska: remove
            f"POST request to {url} with timeout {timeout} and kwargs {kwargs}"
        )
        return self._decode_json_response(
            self._session.post(url, timeout=timeout, **kwargs)
        )

    def get(self, endpoint, timeout=5, **kwargs):
        url = urljoin(self._rest_root, endpoint)
        log.info(  # TODO@dominikatrojanowska: remove
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

    def authenticate(self, user_name: str, password: str):
        response = self.post(
            "auth/login",
            json={"plugin": "ad", "login": user_name, "password": password},
        )
        token = self._get_auth_token(response)
        self._session.headers.update({"Authorization": f"Bearer {token}"})

    # def refresh_token(self):
    #     response = self.post("auth/refresh")
    #     token = self._get_auth_token(response)
    #     self._session.headers.update({"Authorization": f"Bearer {token}"})

    def update_proxies(self, proxy: dict):
        self._session.proxies.update(proxy)

    # def store_ssx_collection_parameters(self, ssx_data: dict):
    #     response = self.post("ssx/datacollection/", json=ssx_data)
    #     if response.status_code != 200:
    #         raise Exception(
    #             "Failed to store SSX collection parameters in PY-ISPyB. "
    #             f"Status code: {response.status_code}, Response: {response.text}"
    #         )

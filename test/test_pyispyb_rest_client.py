from datetime import datetime, timedelta, timezone
from json.decoder import JSONDecodeError
from unittest.mock import MagicMock

import pytest

from mxcubecore.HardwareObjects.abstract.PyISPyBRestClient import (
    AuthenticationExpired,
    NoTokenException,
    PyISPyBRestClient,
    PyISPyBUnsuccessfulResponse,
)


@pytest.fixture
def client():
    return PyISPyBRestClient(rest_root="http://localhost/ispyb/api/v1/")


def build_response(
    status_code=200,
    json_data=None,
    text="ok",
):
    response = MagicMock()

    response.status_code = status_code
    response.text = text
    response.url = "http://localhost/ispyb/api/v1/test"

    if isinstance(json_data, Exception):
        response.json.side_effect = json_data
    else:
        response.json.return_value = json_data

    return response


# =========================================================
# AUTHENTICATION
# =========================================================


def test_authenticate_success(client):
    login_response = {
        "token": "access-token",
        "refreshToken": "refresh-token",
        "expiresIn": 300,
    }
    client.post = MagicMock(return_value=login_response)

    client.authenticate(user_name="testusr", token="testtkn")  # noqa: S106

    client.post.assert_called_once_with(
        "auth/login",
        json={"plugin": "keycloak", "login": "testusr", "token": "testtkn"},
        skip_refresh=True,
    )
    assert client._access_token == "access-token"  # noqa: S105
    assert client._refresh_token == "refresh-token"  # noqa: S105
    assert client._session.headers["Authorization"] == "Bearer access-token"
    assert client._token_expiry is not None


def test_authenticate_without_token_raises(client):
    client.post = MagicMock(return_value={})

    with pytest.raises(NoTokenException):
        client.authenticate(user_name="pyispyb_admin", token="kc-token")  # noqa: S106


# =========================================================
# TOKEN REFRESH
# =========================================================


def test_refresh_access_token_success(client):
    client._refresh_token = "refresh-token"  # noqa: S105
    response = build_response(
        json_data={
            "token": "new-access-token",
            "refreshToken": "new-refresh-token",
            "expiresIn": 300,
        }
    )
    client._session.post = MagicMock(return_value=response)

    client._refresh_access_token()

    assert client._access_token == "new-access-token"  # noqa: S105
    assert client._refresh_token == "new-refresh-token"  # noqa: S105
    assert client._session.headers["Authorization"] == "Bearer new-access-token"


def test_refresh_access_token_without_refresh_token_raises(client):
    client._refresh_token = None

    with pytest.raises(AuthenticationExpired):
        client._refresh_access_token()


def test_refresh_access_token_failure_raises(client):
    client._refresh_token = "invalid-token"  # noqa: S105
    response = build_response(
        status_code=401,
        text="Unauthorized",
    )
    client._session.post = MagicMock(return_value=response)

    with pytest.raises(AuthenticationExpired):
        client._refresh_access_token()


def test_refresh_access_token_malformed_response(client):
    client._refresh_token = "refresh-token"  # noqa: S105
    response = build_response(
        json_data=JSONDecodeError(
            "invalid json",
            "doc",
            0,
        )
    )
    client._session.post = MagicMock(return_value=response)

    with pytest.raises(AuthenticationExpired):
        client._refresh_access_token()


# =========================================================
# GET REQUESTS
# =========================================================


def test_get_success(client):
    client._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    response = build_response(json_data={"ok": True})
    client._session.get = MagicMock(return_value=response)

    result = client.get("users")

    assert result == {"ok": True}
    client._session.get.assert_called_once()


def test_get_refreshes_expired_token(client):
    client._token_expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
    client._refresh_access_token = MagicMock()
    response = build_response(json_data={"ok": True})
    client._session.get = MagicMock(return_value=response)

    client.get("users")

    client._refresh_access_token.assert_called_once()


def test_get_retries_after_401(client):
    client._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    unauthorized = build_response(
        status_code=401,
        text="Unauthorized",
    )
    success = build_response(json_data={"ok": True})
    client._session.get = MagicMock(side_effect=[unauthorized, success])
    client._refresh_access_token = MagicMock()

    result = client.get("users")

    assert result == {"ok": True}
    client._refresh_access_token.assert_called_once()
    assert client._session.get.call_count == 2


# =========================================================
# POST REQUESTS
# =========================================================


def test_post_success(client):
    client._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    response = build_response(json_data={"created": True})
    client._session.post = MagicMock(return_value=response)

    result = client.post(
        "users",
        json={"name": "mohsen"},
    )

    assert result == {"created": True}


# =========================================================
# RESPONSE DECODING
# =========================================================


def test_decode_json_response_returns_results(client):
    response = build_response(json_data={"results": [1, 2, 3]})

    result = client.decode_json_response(response)

    assert result == [1, 2, 3]


def test_decode_json_response_returns_json(client):
    response = build_response(json_data={"ok": True})

    result = client.decode_json_response(response)

    assert result == {"ok": True}


def test_decode_json_response_raises_on_http_error(client):
    response = build_response(
        status_code=500,
        text="Server error",
    )

    with pytest.raises(PyISPyBUnsuccessfulResponse):
        client.decode_json_response(response)


def test_decode_json_response_raises_on_invalid_json(client):
    response = build_response(
        json_data=JSONDecodeError(
            "invalid json",
            "doc",
            0,
        )
    )

    with pytest.raises(JSONDecodeError):
        client.decode_json_response(response)


# =========================================================
# STORE TOKENS
# =========================================================


def test_store_tokens_success(client):
    tokens = {
        "token": "new-access-token",
        "refreshToken": "new-refresh-token",
        "expiresIn": 300,
    }

    client._store_tokens(tokens)

    assert client._access_token == "new-access-token"  # noqa: S105
    assert client._refresh_token == "new-refresh-token"  # noqa: S105
    assert client._session.headers["Authorization"] == "Bearer new-access-token"


@pytest.mark.parametrize("tokens", [None, [], 0])
def test_store_tokens_wrong_response_type(tokens, client):
    with pytest.raises(NoTokenException):
        client._store_tokens(tokens)


def test_store_tokens_missing_access_token(client):
    tokens = {
        "refreshToken": "new-refresh-token",
        "expiresIn": 300,
    }
    with pytest.raises(NoTokenException):
        client._store_tokens(tokens)


# =========================================================
# PROXIES
# =========================================================


def test_update_proxies(client):
    proxies = {
        "http": "http://proxy",
        "https": "https://proxy",
    }

    client.update_proxies(proxies)

    assert client._session.proxies["http"] == "http://proxy"
    assert client._session.proxies["https"] == "https://proxy"

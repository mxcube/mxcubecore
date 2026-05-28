from json.decoder import JSONDecodeError
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

PYISPYB_AUTH_ERROR_MESSSAGE = "Could not verify"

REST_ROOT = "http://example.com/rest/"
USER = "testusr"
TOKEN = "testtkn"  # noqa: S105


@pytest.fixture
@patch("mxcubecore.HardwareObjects.abstract.AbstractLims.HWR")
@patch("mxcubecore.HardwareObjects.abstract.ISPyBAbstractLims.HWR")
@patch("mxcubecore.HardwareObjects.abstract.PyISPyBRestClient.Session")
@patch("mxcubecore.HardwareObjects.UserTypeISPyBLims.Client")
def ispyb_lims(_suds_mock, session_mock, _hwr_mock, hwr_mock):
    # make sure mocked session HWOBJ have session set
    hwr_mock.beamline.session.beamline_name = "ID42"

    # import ISPyBLims first here, so that our mock-patching works
    from mxcubecore.HardwareObjects.MAXIV.ISPyBLims import ISPyBLims

    lims = ISPyBLims(name="dummy")
    lims._config = lims.HOConfig(  # noqa: SLF001
        pyispyb_rest_root=REST_ROOT
    )
    lims.init()

    return lims, session_mock.return_value.post


@pytest.fixture
def json_decode_error():
    doc = MagicMock()
    doc.count.return_value = 0

    return JSONDecodeError("mocked-err", doc, 0)


# @patch("requests.Session")
def test_login_ok(ispyb_lims):
    """test the case when user logs in successfully"""
    ispyb_lims, post_mock = ispyb_lims

    # mock the ISPyB client to return valid token on POST request
    response_mock = MagicMock(
        url=f"{REST_ROOT}auth/login",
        status_code=200,
        text="dummy-text",
    )
    post_mock.return_value = response_mock
    response_mock.json.return_value = {"token": "dummy-token"}

    is_ok, err = ispyb_lims.ispyb_login(USER, TOKEN)

    # check that we got 'login ok' result
    assert is_ok
    assert err is None

    # check that correct POST request was made
    post_mock.assert_called_once_with(
        f"{REST_ROOT}auth/login",
        json={
            "plugin": "keycloak",
            "login": USER,
            "token": TOKEN,
        },
        timeout=5,
    )


def test_login_invalid_credentials(ispyb_lims, json_decode_error):
    """test the case when user fails to login due to wrong credentials"""
    ispyb_lims, post_mock = ispyb_lims

    # mock ISPyB 'login failed' response,
    response_mock = MagicMock(
        url=f"{REST_ROOT}auth/login",
        status_code=401,
        text=PYISPYB_AUTH_ERROR_MESSSAGE,
    )
    post_mock.return_value = response_mock
    response_mock.json.side_effect = json_decode_error

    is_ok, err = ispyb_lims.ispyb_login(USER, TOKEN)

    # check that we got 'login failed' result
    assert not is_ok
    assert (
        err == f"Request to {REST_ROOT}auth/login failed with code: 401. "
        f"Response: {PYISPYB_AUTH_ERROR_MESSSAGE}"
    )

    post_mock.assert_called_once_with(
        f"{REST_ROOT}auth/login",
        json={
            "plugin": "keycloak",
            "login": USER,
            "token": TOKEN,
        },
        timeout=5,
    )

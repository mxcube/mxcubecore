from json.decoder import JSONDecodeError
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

ISPYB_AUTH_ERROR_MESSSAGE = (
    "JBAS011843: Failed instantiate InitialContextFactory com.sun.jndi.ldap.LdapCtxFactory "
    'from classloader ModuleClassLoader for Module "deployment.ispyb.ear.ispyb-ws.war:main" '
    "from Service Module Loader"
)

REST_ROOT = "http://example.com/rest/"
USER = "testusr"
PASS = "testpsd"

# @patch("suds.client.Client")
# @patch("mxcubecore.HardwareRepository")


@pytest.fixture
@patch("mxcubecore.HardwareObjects.abstract.AbstractLims.HWR")
@patch("mxcubecore.HardwareObjects.abstract.ISPyBAbstractLims.HWR")
@patch("mxcubecore.HardwareObjects.abstract.ISPyBDataAdapter.Client")
def ispyb_lims(_suds_mock, _hwr_mock, hwr_mock):
    # make sure mocked session HWOBJ have session set
    hwr_mock.beamline.session.beamline_name = "ID42"

    # import ISPyBLims first here, so that our mock-patching works
    from mxcubecore.HardwareObjects.MAXIV.ISPyBLims import ISPyBLims

    lims = ISPyBLims(name="dummy")
    lims.set_property("ws_root", "http://example.com/tstWS/")
    lims.set_property("rest_root", REST_ROOT)
    lims.init()

    return lims


@pytest.fixture
def json_decode_error():
    doc = MagicMock()
    doc.count.return_value = 0

    return JSONDecodeError("mocked-err", doc, 0)


@patch("requests.post")
def test_login_ok(post_mock, ispyb_lims):
    """test the case when user logs in successfully"""

    # mocks the ISPyB client to return valid token on POST request
    post_mock.return_value.json.return_value = dict(token="dummy-token")

    is_ok, err = ispyb_lims.ispyb_login(USER, PASS)

    # check that we got 'login ok' result
    assert is_ok
    assert err is None

    # check that correct POST request was made
    post_mock.assert_called_once_with(
        f"{REST_ROOT}authenticate?site=MAXIV",
        data={"login": USER, "password": PASS},
    )


@patch("requests.post")
def test_login_invalid_credentials(post_mock, ispyb_lims, json_decode_error):
    """test the case when user fails to login due to wrong credentials"""

    #
    # mock ISPyB 'login failed' response,
    # yes, this is how ISPyB replies at MAXIV
    #
    response_mock = MagicMock()
    response_mock.text = ISPYB_AUTH_ERROR_MESSSAGE
    response_mock.json.side_effect = json_decode_error

    post_mock.return_value = response_mock

    is_ok, err = ispyb_lims.ispyb_login(USER, PASS)

    # check that we got 'login failed' result
    assert not is_ok
    assert err == "invalid credentials"

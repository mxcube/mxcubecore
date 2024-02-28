# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Test for the XRF spectrum procedure. Mostly testing the AbstractXRFSpectrum.
Using configuration file:
<object class="XRFSpectrumMockup">
  <default_integration_time>2</default_integration_time>
</object>

"""
__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import pytest
from test.pytest import TestHardwareObjectBase
from mxcubecore.BaseHardwareObjects import HardwareObjectState


@pytest.fixture
def test_object(beamline):
    """Get the test object from beamline.yml"""
    result = beamline.xrf_spectrum
    yield result


class TestXRF(TestHardwareObjectBase.TestHardwareObjectBase):
    """Test suite"""
    def test_xrf_init(self, test_object):
        """Check initialisation"""
        assert (
            test_object is not None
        ), "XRF hardware objects is None (not initialized)"
        assert test_object.default_integration_time == 2

    def test_start_xrf_spectrum(self, test_object):
        """Test start_xrf_spectrum, including:
           - create_directory
           - get_filename
           - get the session ID from lims, if possible
        """
        session_id = 12345
        blsample_id = 11
        if test_object.lims:
            session = test_object.lims.get_proposal(1, 2).get("Session")
            if isinstance(session, list):
                session_id = session[0].get("sessionId")
        catcher = TestHardwareObjectBase.SignalCatcher()
        test_object.connect("stateChanged", catcher.catch)
        ret = test_object.start_xrf_spectrum(
            test_object.default_integration_time,
            prefix="xrftst",
            data_dir="/tmp/abb",
            archive_dir="/tmp",
            session_id=session_id,
            blsample_id=blsample_id,
        )
        state = catcher.async_result.get_nowait()
        assert state == HardwareObjectState.BUSY
        test_object.disconnect("stateChanged", catcher.catch)
        assert ret is True

    def test_start_xrf_spectrum_error(self, test_object):
        """Test start_xrf_spectrum error handling:
           - try to create directory to /, which should give an error
        """
        catcher = TestHardwareObjectBase.SignalCatcher()
        test_object.connect("stateChanged", catcher.catch)
        catcher1 = TestHardwareObjectBase.SignalCatcher()
        test_object.connect("xrfSpectrumStatusChanged", catcher1.catch)
        ret = test_object.start_xrf_spectrum(
            test_object.default_integration_time,
            prefix="xrftst",
            data_dir="/abcd",
            session_id=12345,
            blsample_id=8,
        )
        state = catcher.async_result.get_nowait()
        assert state == HardwareObjectState.FAULT
        test_object.disconnect("stateChanged", catcher.catch)

        msg = catcher1.async_result.get_nowait()
        assert msg == "Error creating directory"
        test_object.disconnect("xrfSpectrumStatusChanged", catcher1.catch)

        assert ret is False

    def test_execute_xrf_spectrum(self, test_object):
        """Test the execute_xrf_spectrum, which includes
           spectrum_command_finished and spectrum_store_lims"""
        catcher = TestHardwareObjectBase.SignalCatcher()
        test_object.connect("stateChanged", catcher.catch)
        test_object.execute_xrf_spectrum(test_object.default_integration_time)
        state = test_object.get_state()
        assert state == HardwareObjectState.READY
        state = catcher.async_result.get_nowait()
        assert state == HardwareObjectState.READY
        test_object.disconnect("stateChanged", catcher.catch)

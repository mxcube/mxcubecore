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

__copyright__ = """ Copyright © 2019-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import pytest

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from test.pytest import TestAbstractNStateBase


@pytest.fixture
def test_object(beamline):
    result = beamline.safety_shutter
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestShutter(TestAbstractNStateBase.TestAbstractNStateBase):
    def test_shutter_init(self, test_object):
        assert (
            test_object is not None
        ), "Shutter hardware objects is None (not initialized)"

        # The methods are defined with abc.abstractmethod which will raise
        # an exception if the method is not defined. So there is no need to
        # test for the presence of each method
        print(f"state is {test_object.get_state()}")
        assert test_object.get_state() == HardwareObjectState.READY

    def test_shutter_open_close(self, test_object):
        test_object.open(timeout=None)
        assert test_object.is_open is True

        assert test_object.get_state() == HardwareObjectState.READY

        test_object.close(timeout=None)
        assert test_object.is_open is False

    def test_shutter_value(self, test_object):
        for val in test_object.VALUES:
            test_object.set_value(val, timeout=None)
            assert test_object.get_value() == val

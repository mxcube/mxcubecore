# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2019-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import pytest

from HardwareRepository.test.pytest import TestAbstractActuatorBase

@pytest.fixture
def test_object(beamline):
    result = beamline.transmission
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO

class TestTransmission(TestAbstractActuatorBase.TestAbstractActuatorBase):


    def test_transmission_attributes(self, beamline, test_object):
        assert (
            not beamline.energy is None
        ), "Transmission hardware object is None (not initialized)"

        value = test_object.get_value()
        limits = test_object.get_limits()

        assert isinstance(value, (int, float)), (
            "Transmission value has to be int or float"
        )
        assert None not in limits, "One or several limits is None"
        assert limits[0] < limits[1], "Transmission limits define an invalid range"


    def test_transmission_methods(self, test_object):
        target = 60.0
        test_object.set_value(target, timeout=None)
        assert test_object.get_value() == target

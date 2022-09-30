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

"""Test suite for AbstractFlux"""

__copyright__ = """ Copyright © 2019-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

from test.pytest import TestAbstractActuatorBase
import pytest

@pytest.fixture
def test_object(beamline):
    """Use the flux object from beamline"""
    result = beamline.flux
    yield result

class TestFlux(TestAbstractActuatorBase.TestAbstractActuatorBase):
    """Test Flux methods"""

    def test_initial_value(self, test_object):
        """Overload this as get_value gives random numbers"""
        assert (
            test_object is not None
        ), "Flux hardware objects is None (not initialized)"

        # start value should be the default value.
        startval = test_object.default_value

        assert startval is not None, "initial value may not be None"
        msg = f"get_value() {startval} differs from _nominal_value {test_object._nominal_value}"
        assert test_object._nominal_value == startval, msg

    def test_flux_attributes(self, test_object):
        """Test the attrubutes"""
        assert test_object.read_only is True
        value = test_object.get_value()
        print(f"------> Flux is {value}")
        assert isinstance(value, (int, float)), "Flux value has to be int or float"

        assert test_object.is_beam is True

    def test_flux_methods(self, test_object):
        """Test the methods"""
        # Test timeout - expecting to have RuntimeError
        with pytest.raises(RuntimeError) as info:
            test_object.wait_for_beam(0)

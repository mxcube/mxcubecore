# encoding: utf-8
#
#  Project name: MXCuBE
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

import pytest

from test import TestAbstractActuatorBase


@pytest.fixture
def test_object(beamline):
    """Use the dose_rate object from beamline"""
    return beamline.dose_rate


class TestDoseRate(TestAbstractActuatorBase.TestAbstractActuatorBase):
    """Test DoseRate"""

    def test_initial_value(self, test_object):
        assert test_object is not None, (
            "DoseRate hardware objects is None (not initialized)"
        )

        # value should never be None
        assert test_object.get_value() is not None, "initial value may not be None"

    def test_attributes(self, test_object):
        """Test the attributes"""
        assert test_object.read_only is True
        assert test_object.get_limits() == test_object._nominal_limits

    def test_methods(self, test_object):
        value = test_object.get_value()
        print(f"------> Dose rate is {value}")
        assert isinstance(value, (int, float)), "Dose rate should be int or float"

        with pytest.raises(ValueError):
            test_object.set_value(value)

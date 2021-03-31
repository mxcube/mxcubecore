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

from test.pytest import TestAbstractActuatorBase


@pytest.fixture
def test_object(beamline):
    result = beamline.energy
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestEnergy(TestAbstractActuatorBase.TestAbstractActuatorBase):
    def test_energy_atributes(self, test_object):

        assert (
            test_object is not None
        ), "Energy hardware objects is None (not initialized)"
        current_energy = test_object.get_value()
        current_wavelength = test_object.get_wavelength()
        energy_limits = test_object.get_limits()
        wavelength_limits = test_object.get_wavelength_limits()

        assert isinstance(current_energy, float), "Energy value has to be float"
        assert isinstance(current_wavelength, float), "Energy value has to be float"
        # Propose to insist on tuple - to avoid exporting mutable lists
        assert isinstance(
            energy_limits, tuple
        ), "Energy limits has to be defined as tuple or list"
        assert isinstance(
            wavelength_limits, tuple
        ), "Energy limits has to be defined as tuple or list"
        assert not None in energy_limits, "One or several energy limits is None"
        assert not None in wavelength_limits, "One or several wavelength limits is None"
        assert (
            energy_limits[0] < energy_limits[1]
        ), "First value of energy limits has to be the low limit"

    def test_energy_methods(self, test_object):
        target = 12.7
        test_object.set_value(target, timeout=None)
        assert test_object.get_value() == target

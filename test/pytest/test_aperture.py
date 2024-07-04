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

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import pytest
from test.pytest.TestAbstractNStateBase import TestAbstractNStateBase


@pytest.fixture
def test_object(beamline):
    result = beamline.diffractometer.aperture
    yield result


class TestAperture(TestAbstractNStateBase):
    def test_aperture_atributes(self, test_object):
        assert (
            test_object is not None
        ), "Aperture hardware objects is None (not initialized)"
        current_value = test_object.get_value()
        assert current_value in test_object.VALUES

    def test_initialise_values_from_default(self, test_object):
        values = test_object.VALUES
        test_object._initialise_values()
        assert values != test_object.VALUES
        test_object._initialise_inout()
        assert hasattr(test_object.VALUES, "IN")

    def test_get_factor(self, test_object):
        for value in test_object.VALUES:
            _nam = value.name
            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                assert value.value[1] == test_object.get_factor(_nam)
                assert value.value[1] == test_object.get_factor(value)

    def test_size(self, test_object):
        test_object._initialise_inout()
        for label in test_object.get_diameter_size_list():
            test_object.set_value(test_object.VALUES[label])
            test_object.update_value(test_object.VALUES[label])
            assert float(test_object.VALUES[label].value[0]) == test_object.get_size(label)
            assert test_object.VALUES[label] == test_object.get_value()

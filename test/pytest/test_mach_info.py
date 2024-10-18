#! /usr/bin/env python
# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""Test suite for MachineInfo hardware object
"""

from test.pytest import TestHardwareObjectBase

import pytest

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the machine_info object from beamline"""
    result = beamline.machine_info
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestMachineInfo(TestHardwareObjectBase.TestHardwareObjectBase):
    """MachineInfo uses the HardwareObject tests."""

    def test_mach_info_atributes(self, test_object):
        """Test for attributes"""
        assert (
            test_object is not None
        ), "Machine info hardware object is None (not initialized)"
        assert isinstance(
            test_object.get_current(), (int, float)
        ), "current value has to be int or float"
        assert isinstance(
            test_object.get_message(), (str)
        ), "message value has to be string"
        assert isinstance(
            test_object.get_lifetime(), (int, float)
        ), "lifetime value has to be int or float"
        assert isinstance(
            test_object.get_topup_remaining(), (int, float)
        ), "topup_remaining value has to be int or float"
        assert isinstance(
            test_object.get_value(), dict
        ), "Machine info dictionary has to be dict"

    def test_get_value(self, test_object):
        """Test the get_value and the valueChanged signal"""
        catcher = TestHardwareObjectBase.SignalCatcher()
        test_object.connect("valueChanged", catcher.catch)
        value = catcher.async_result.get()
        test_object.disconnect("valueChanged", catcher.catch)
        assert value.get("current") is not None

    def test_check_attributes(self, test_object):
        """Check if the attributes required have a methof for reading"""
        test_object._mach_info_dict.update({"wrong_name": None})
        attr_list = list(test_object._mach_info_dict.keys())
        test_object._check_attributes(attr_list)
        assert "wrong_name" not in test_object._mach_info_keys

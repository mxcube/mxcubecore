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
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import pytest
from mx3core.test.pytest import TestHardwareObjectBase

__copyright__ = """ Copyright © 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    result = beamline.machine_info
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO


class TestMachineInfo(TestHardwareObjectBase.TestHardwareObjectBase):
    def test_mach_info_atributes(self, test_object):
        assert (
            test_object is not None
        ), "Machine info hardware object is None (not initialized)"
        current = test_object.get_current()
        message = test_object.get_message()
        lifetime = test_object.get_lifetime()
        topup_remaining = test_object.get_topup_remaining()
        mach_info_dict = test_object.get_mach_info_dict()

        assert isinstance(
            mach_info_dict, dict
        ), "Machine info dictionary has to be dict"

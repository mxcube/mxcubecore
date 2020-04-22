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
from HardwareRepository.test.pytest import TestAbstractMotorBase

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "08/04/2020"

@pytest.fixture
def test_object(beamline):
    result = beamline.diffractometer.omega
    yield result
    # Cleanup code here - restores starting state for next call:
    # NBNB TODO

class TestOmegaMotor(TestAbstractMotorBase.TestAbstractMotorBase):


    def test_value_wrap(self, test_object):
        """Test wrap_range"""
        wrap_range = test_object._wrap_range
        if wrap_range:

            limits = test_object.get_limits()
            if None in limits or limits[0] == limits[1]:
                limits = (0, wrap_range)
            low, high = limits
            tol = test_object._tolerance or 0.001
            toobig = low + wrap_range + 0.1 * (high - low)
            test_object.set_value(toobig, timeout=None)
            assert abs(test_object.get_value() - low - 0.1 * (high - low)) < tol, (
                "Set value %s does not wrap to %s; result is %s"
                % (toobig, low + 0.1 * (high - low), test_object.get_value())
            )



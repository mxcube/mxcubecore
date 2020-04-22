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

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "09/04/2020"

import abc
import pytest
from HardwareRepository.test.pytest import TestAbstractActuatorBase

test_object = TestAbstractActuatorBase.test_object


class TestAbstractNStateBase(TestAbstractActuatorBase.TestAbstractActuatorBase):
    """Tests for AbstractNState subclasses"""

    __metaclass__ = abc.ABCMeta

    def test_values(self, test_object):
        """Test there are at last trhee values, including UNKNOWN"""

        assert len(test_object.VALUES) > 2, (
            "Less than three values in enumeration; %s" % test_object.VALUES
        )

        assert test_object.VALUES.UNKNOWN.value == "UNKNOWN", (
            "Walue 'UNKNOWN' missing from enumeration: %s" % test_object.VALUES
        )

    def test_limits_setting(self, test_object):
        """Test that set_limits and update_limits are diabled
        NB override ,ocally if you have an NState with limits"""
        limits = test_object.get_limits()
        with pytest.raises(NotImplementedError):
            test_object.update_limits(limits)
        with pytest.raises(NotImplementedError):
            test_object.set_limits(limits)

    def test_setting_timeouts_1(self, test_object):
        """Test that setting with timeout=0 works,
        and that wait_ready raises an error afterwards
        Using actual values"""
        if test_object.read_only:
            return

        values = list(val for val in test_object.VALUES if val != "UNKNOWN")
        val1, val2 = values[:2]

        # Must be set first so the next command causes a change
        test_object.set_value(val1, timeout=90)
        with pytest.raises(BaseException):
            test_object.set_value(val2, timeout=1.0e-6)

    def test_setting_timeouts_2(self, test_object):
        """Test that setting with timeout=0 works,
        and that wait_ready raises an error afterwards
        Using actual values"""
        if test_object.read_only:
            return

        values = list(val for val in test_object.VALUES if val != "UNKNOWN")
        val1, val2 = values[:2]

        # Must be set first so the next command causes a change
        test_object.set_value(val2, timeout=None)
        with pytest.raises(BaseException):
            test_object.set_value(val1, timeout=0)
            test_object.wait_ready(timeout=1.0e-6)

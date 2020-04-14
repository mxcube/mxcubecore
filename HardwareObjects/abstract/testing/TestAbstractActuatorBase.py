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
import time
import gevent
import pytest

from HardwareRepository.HardwareObjects.abstract.testing import TestHardwareObjectBase

test_object = TestHardwareObjectBase.test_object


class TestAbstractActuatorBase(TestHardwareObjectBase.TestHardwareObjectBase):
    """Tests for AbstractActuator subclasses"""

    __metaclass__ = abc.ABCMeta

    def test_value_setting(self, test_object):
        startval = test_object.get_value()
        assert startval is not None, "initial value may not be None"

        if test_object.default_value is not None:
            assert startval == test_object.default_value, (
                "Initial value %s different from default value %s"
                % (startval, test_object.default_value)
            )

        assert test_object._nominal_value == startval, (
            "get_value() %s differs from _nominal_value %s"
            % (startval, test_object._nominal_value)
        )

        test_object.update_value()
        assert (
            test_object._nominal_value == startval
        ), "Updating value to None does not set to get_value()"

        test_object._nominal_value = None
        test_object.update_value(startval)
        assert test_object._nominal_value == startval, (
            "update_value(%s) leaves _nominal_value as %s"
            % (startval, test_object._nominal_value)
        )

        if not test_object.read_only:
            test_object._nominal_value = None
            test_object._set_value(startval)
            test_object.wait_ready()
            assert test_object._nominal_value == startval, (
                "_set_value(%s) leaves _nominal_value as %s"
                % (startval, test_object._nominal_value),
            )

            test_object._nominal_value = None
            test_object.set_value(startval, timeout=None)
            assert test_object._nominal_value == startval, (
                "Setting to %s leaves _nominal_value aa %s"
                % (startval, test_object._nominal_value),
            )

    def test_limits_type(self, test_object):
        limits = test_object.get_limits()
        assert isinstance(limits, tuple), (
            "AbstractActuator limits must be a tuple, are %s" % limits
        )
        assert len(limits) == 2, (
            "AbstractActuator limits must be length 2, are %s" % limits
        )

    def test_limits_setting(self, test_object):
        limits = test_object.get_limits()
        if limits != (None, None):
            test_object.update_limits((None, None))
            assert test_object._nominal_limits == (None, None), (
                "Update limits to (None, None) but _nominal_limits value is %s"
                % (test_object._nominal_limits,)
            )

            test_object.update_limits(limits)
            assert test_object._nominal_limits == limits, (
                "Updated limits to %s but _nominal_limits is %s"
                % (limits, test_object._nominal_limits)
            )
            if not test_object.read_only:
                test_object._nominal_limits = (None, None)
                test_object.set_limits(limits)
                assert test_object._nominal_limits == limits, (
                    "Set limits to %s but _nominal_limits is %s"
                    % (limits, test_object._nominal_limits)
                )

    def test_setting_readonly(self, test_object):
        if test_object.read_only:
            with pytest.raises(ValueError):
                test_object.set_value(test_object.default_value)

    def test_validate_value(self, test_object):
        start_val = test_object.get_value()
        assert test_object.validate_value(start_val), (
            "Staring valuee %s evaluates invalid" % start_val
        )
        default_limits = test_object.get_limits()
        if test_object.read_only:
            assert default_limits == (start_val, start_val), (
                "read_only default limits %s do not match starting value %s"
                % (default_limits, start_val)
            )

    def test_setting_timeouts_1(self, test_object):
        # NB this test may need adjusting
        if test_object.read_only:
            return
        startval = test_object.get_value()

        test_object._nominal_value = None
        with pytest.raises(BaseException):
            test_object.set_value(startval, timeout=1.0e-6)

    def test_setting_timeouts_2(self, test_object):
        # NB this test may need adjusting
        if test_object.read_only:
            return
        startval = test_object.get_value()

        test_object._nominal_value = None
        with pytest.raises(BaseException):
            test_object.set_value(startval, timeout=0)
            test_object.wait_ready(timeout=1.0e-6)

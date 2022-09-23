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
# along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.

"""Test suite for AbstractActuator class"""

__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__date__ = "09/04/2020"

from test.pytest import TestHardwareObjectBase

import abc
import gevent
import pytest


test_object = TestHardwareObjectBase.test_object


class TestAbstractActuatorBase(TestHardwareObjectBase.TestHardwareObjectBase):
    """Tests for AbstractActuator subclasses"""

    __metaclass__ = abc.ABCMeta

    def test_initial_value(self, test_object):
        """Test initial and default values for newly loaded object"""
        startval = test_object.get_value()
        assert startval is not None, "initial value may not be None"

        assert test_object._nominal_value == startval, (
            "get_value() %s differs from _nominal_value %s"
            % (startval, test_object._nominal_value)
        )

        if test_object.default_value is not None:
            assert startval == test_object.default_value, (
                "Initial value %s different from default value %s"
                % (startval, test_object.default_value)
            )

    def test_value_setting(self, test_object):
        """Test effect of update_value and (if not read_only) set_value"""

        # do not run if read_only object
        if test_object.read_only:
            return

        startval = test_object.get_value()

        test_object.update_value()
        assert (
            test_object._nominal_value == startval
        ), "Updating value to None does not set to get_value()"

        # Must be set to None so the next command causes a change
        test_object._nominal_value = None
        test_object.update_value(startval)
        assert test_object._nominal_value == startval, (
            "update_value(%s) leaves _nominal_value as %s"
            % (startval, test_object._nominal_value)
        )

        if not test_object.read_only:
            # Test set_value with and without a timeout (different code branches)
            # Must be set to None so the next command causes a change
            test_object._nominal_value = None
            test_object._set_value(startval)
            test_object.wait_ready()
            assert test_object._nominal_value == startval, (
                "_set_value(%s) leaves _nominal_value as %s"
                % (startval, test_object._nominal_value),
            )

            # Must be set to None so the next command causes a change
            test_object._nominal_value = None
            test_object.set_value(startval, timeout=None)
            assert test_object._nominal_value == startval, (
                "Setting to %s leaves _nominal_value aa %s"
                % (startval, test_object._nominal_value),
            )

    def test_limits_type(self, test_object):
        """Test the limits"""
        limits = test_object.get_limits()
        assert isinstance(limits, tuple), (
            f"AbstractActuator limits must be a tuple, are {limits}"
        )
        assert len(limits) == 2, (
            "AbstractActuator limits must be length 2, are {limits}"
        )

    def test_limits_setting(self, test_object):
        """Test update_limits and (if not read_oinly) set_limits"""
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
                # Must be set to (None, None) so the next command causes a change
                test_object._nominal_limits = (None, None)
                test_object.set_limits(limits)
                assert test_object._nominal_limits == limits, (
                    "Set limits to %s but _nominal_limits is %s"
                    % (limits, test_object._nominal_limits)
                )

    def test_setting_readonly(self, test_object):
        """Test that setting is disabled for read_only"""
        if test_object.read_only:
            with pytest.raises(ValueError):
                test_object.set_value(test_object.default_value)

    def test_validate_value(self, test_object):
        """Ensure that initial value tests valid, """
        start_val = test_object.get_value()
        assert test_object.validate_value(start_val), (
            "Staring valuee %s evaluates invalid" % start_val
        )

    def test_setting_timeouts_1(self, test_object):
        """Test that setting is not istantaneuos,
        and that timeout is raised only if too slow"""
        if test_object.read_only:
            return
        startval = test_object.get_value()
        test_object.set_value(startval, timeout=180)

        # Must be set to None so the next command causes a change
        test_object._nominal_value = None
        with pytest.raises(RuntimeError):
            test_object.set_value(startval, timeout=1.0e-6)

    def test_setting_timeouts_2(self, test_object):
        """Test that setting with timeout=0 works,
        and that wait_ready raises an error afterwards"""
        if test_object.read_only:
            return
        startval = test_object.get_value()
        test_object.set_value(startval, timeout=0)

        # Must be set to None so the next command causes a change
        test_object._nominal_value = None
        with pytest.raises(RuntimeError):
            test_object.set_value(startval, timeout=0)
            test_object.wait_ready(timeout=1.0e-6)

    def test_signal_value_changed(self, test_object):
        catcher = TestHardwareObjectBase.SignalCatcher()
        val = test_object.get_value()
        # Must be set to None so the next command causes a change
        test_object._nominal_value = None
        test_object.connect("valueChanged", catcher.catch)
        try:
            test_object.update_value(val)
            # Timeout to guard against waiting foreer if signal is not sent)
            with gevent.Timeout(30):
                result = catcher.async_result.get()
                assert result == val
        finally:
            test_object.disconnect("valueChanged", catcher.catch)

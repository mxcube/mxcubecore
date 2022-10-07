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
"""
Test the resolution hardware object. Dependant on detector_distance and energy
hardware objects
"""
from test.pytest import TestAbstractMotorBase
import pytest


__copyright__ = """ Copyright © 2016 - 2022 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def test_object(beamline):
    """Use the resolution object from beamline-setup.yml"""
    result = beamline.resolution
    yield result


class TestResolution(TestAbstractMotorBase.TestAbstractMotorBase):
    """Overload some of the AbstractMotor tests, as resolution depends on
       the detector_distance mock motor.
    """

    def test_limits_setting(self, test_object):
        """Cannot set resolution limits, but read the detector distance
           limits and check calculation for resolution limits.
        """
        limits = test_object.get_limits()
        if limits != (None, None):
            test_object.update_limits((None, None))
            msg = "Update limits to (None, None) but "
            msg += f"_nominal_limits value is {test_object._nominal_limits}"
            assert test_object._nominal_limits == (None, None), msg

        with pytest.raises(NotImplementedError):
            test_object._nominal_limits = (None, None)
            test_object.set_limits(limits)

    def test_update_state(self, test_object):
        """The state corresponds to the detector distance motor state.
           As the detector distance state does not change, the test is empty.
        """

    def test_setting_with_tolerance(self, test_object):
        """Update position is dependant on the detector distance motor."""

        low, high = test_object.get_limits() or (0, 1)
        tol = test_object._tolerance
        mid = (low + high) / 2.0

        test_object.set_value(high, timeout=None)
        val = test_object.get_value()
        msg = f"set_value: Difference between value {val} and target "
        msg += f"{high} is bigger than the tolerance {tol}"
        assert abs(val - high) < tol, msg

        toobig = high + 0.1 * (high - low)
        assert not (
            test_object.validate_value(toobig)
        ), f"Too big value {toobig} validates as OK"

        with pytest.raises(ValueError):
            test_object.set_value(toobig, timeout=None)

        # Must be set first so the next command causes a change
        test_object._set_value(low)
        test_object.wait_ready()
        test_object.set_value_relative(0.5 * (high - low), timeout=None)
        val = test_object.get_value()
        msg = f"set_value_relative: Difference between value {val} and target"
        msg += f"{mid} is bigger than the tolerance {tol}"
        assert abs(val - mid) < tol, msg

        test_object.update_value(low)
        test_object.update_value(low + 0.5 * tol)
        assert (
            test_object._nominal_value == low
        ), "update_value result does not respect tolerance cutoff"

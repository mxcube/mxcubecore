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

from collections import OrderedDict

from HardwareRepository.BaseHardwareObjects import (
    HardwareObjectState, HardwareObjectMixin
)
from HardwareRepository.HardwareObjects.abstract import (
    AbstractActuator, AbstractNState, AbstractMotor
)

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "02/04/2020"

def test_state_seting(beamline):
    """Test state atttribute for all HardwareObjects

    Args:
        beamline (Beamline): topmost beamline object
    """
    ho_states = OrderedDict((x.name, x) for x in HardwareObjectState)


    for role, obj in beamline.all_objects_by_role.items():

        if isinstance(obj, HardwareObjectMixin):
            print ('@~@~ HardwareObjectMixin')

            obj._state = obj.STATES.BUSY
            assert obj.get_state() is obj.STATES.BUSY, (
                "Setting %s._state is not reflected in get_state()" % role
            )

            for name, ho_state in ho_states.items():
                assert getattr(obj.STATES, name) is ho_state, (
                    "%s state %s does not match HardwareObjectState.%s"
                    % (role, name, name)
                )

                obj.update_state(ho_state)
                assert obj.get_state() is ho_state, (
                    "%s.update_state(HardwareObjectState.%s) is not reflected in result"
                    % (role, name)
                )

            obj.update_values()


        if isinstance(obj, AbstractActuator.AbstractActuator):

            default = obj.get_value()
            default_limits = obj.get_limits()
            obj.update_value()

            if default is not None:
                print ('@~@~ AbstractActuator default')
                assert obj.validate_value(default), (
                    "%s default value %s evaluated as invalid"
                    % (role, default)
                )
                obj.update_value(default)

                if obj.read_only:
                    assert default_limits == (default, default), (
                        "read_only %s defualt limits %s do not match default value %s"
                        % (role, default_limits, default)
                    )
                else:
                    obj.set_value(default)
                    obj.set_limits(default_limits)

                if obj.read_only and default_limits and None not in default_limits:
                    assert default_limits == (default, default), (
                        "read_only %s defualt limits %s do not match default value %s"
                        % (role, default_limits, default)
                    )

            if not isinstance(obj, AbstractNState.AbstractNState):
                obj.update_limits()
                obj.update_limits(default_limits)
                obj.set_limits(default_limits)

        if isinstance(obj, AbstractMotor.AbstractMotor):

            velocity = obj.get_velocity()
            if velocity:
                vel2 = 0.9 * velocity
                obj.set_velocity(vel2)
                assert obj.get_velocity() == vel2, (
                    "Error setting velocity from %s to %s"
                    % (velocity, vel2)
                )
            limits = obj.get_limits()
            if limits and None not in limits:
                low, high = limits
                tol = obj._tolerance
                if not obj.read_only and low != high:
                    mid = low + high / 2
                    obj.set_value(high)
                    val = obj.get_value()
                    if tol:
                        assert abs(val - high) < tol, (
                            "Erros setting value to upper limit %s, result %s"
                            % (high, val)
                        )
                    obj.update_value(mid)
                    val = obj.get_value()
                    if tol:
                        assert abs(val - mid) < tol, (
                            "Erros updating value to %s, result %s"
                            % (mid, val)
                        )
                    toobig = high + 0.1 * (high - low)
                    assert not obj.validate_value(toobig), (
                        "Too-big value %s validates as OK" % toobig
                    )
                    obj.set_value(low)
                    obj.set_value_relative(0.5 * (high - low))
                    val = obj.get_value()
                    if tol:
                        assert abs(val - mid) < tol, (
                            "set_value_relative result %s more than %s from target %s"
                            % (val, tol, mid)
                        )
                    obj.update_value(mid)
                    assert obj._nominal_value == mid, (
                        "update_value result %s differs from target %s"
                        % (obj._nominal_value, mid)
                    )
                    if tol:
                        obj.update_value(low)
                        obj.update_value(low + 0.5 * tol)
                        assert obj._nominal_value == low, (
                            "update_value result does not respect tolerance cutoff"
                        )

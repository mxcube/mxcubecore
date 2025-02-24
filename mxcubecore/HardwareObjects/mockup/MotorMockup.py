#! /usr/bin/env python
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Example of xml config file

<object class="MotorMockup">
  <username>Mock motor</username>
  <actuator_name>mock_motor</actuator_name>
  <!-- for the mockup only -->
  <default_value>500</default_value>
  <velocity>100</velocity>
  <wrap_range>None</wrap_range>
  <default_limits>[-360, 360]</default_limits>
</object>
"""

import ast
import time

from mxcubecore.HardwareObjects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)
from mxcubecore.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

DEFAULT_VELOCITY = 100
DEFAULT_LIMITS = (-10000, 10000)
DEFAULT_VALUE = 10.124
DEFAULT_WRAP_RANGE = None


class MotorMockup(ActuatorMockup, AbstractMotor):
    """Mock Motor implementation"""

    SPECIFIC_STATES = MotorStates

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self._wrap_range = None

    def init(self):
        """Initialisation method"""
        # get username, actuator_name and tolerance
        super().init()

        # local properties
        if not self.get_velocity():
            self.set_velocity(DEFAULT_VELOCITY)
        if None in self.get_limits():
            self.update_limits(DEFAULT_LIMITS)
        try:
            _wr = self.get_property("wrap_range")
            self._wrap_range = DEFAULT_WRAP_RANGE if not _wr else ast.literal_eval(_wr)
        except (ValueError, SyntaxError):
            self._wrap_range = DEFAULT_WRAP_RANGE
        if self.default_value is None:
            self.default_value = DEFAULT_VALUE
            self.update_value(self.default_value)

        self.update_state(self.STATES.READY)

    def _move(self, value):
        """Simulated motor movement.
        Args:
            value (float): target position
        Returns:
            (float): The reached position.
        """

        self.update_specific_state(self.SPECIFIC_STATES.MOVING)

        start_pos = self.get_value()
        if value is not None and start_pos is not None:
            delta = abs(value - start_pos)

            direction = -1 if value < self.get_value() else 1

            start_time = time.time()

            while (time.time() - start_time) < (delta / self.get_velocity()):
                time.sleep(0.02)
                val = start_pos + direction * self.get_velocity() * (
                    time.time() - start_time
                )

                val = val if not self._wrap_range else val % self._wrap_range

                self.update_value(val)
        time.sleep(0.02)

        _low, _high = self.get_limits()
        if value == self.default_value:
            self.update_specific_state(self.SPECIFIC_STATES.HOME)
        elif value == _low:
            self.update_specific_state(self.SPECIFIC_STATES.LOWLIMIT)
        elif value == _high:
            self.update_specific_state(self.SPECIFIC_STATES.HIGHLIMIT)
        else:
            self.update_specific_state(None)

        return value

    def is_moving(self):
        return ( (self.get_state() == self.STATES.BUSY ) or (self.get_state() == self.SPECIFIC_STATES.MOVING))

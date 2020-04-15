#! /usr/bin/env python
# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Example of xml config file

<device class="MotorMockup">
  <username>Mock motor</username>
  <actuator_name>mock_motor</actuator_name>
  <!-- for the mockup only -->
  <default_value>500</default_value>
  <velocity>100</velocity>
  <wrap_range>None</wrap_range>
  <default_limits>[-360, 360]</default_limits>
</device>
"""

import time
import ast
import gevent
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

DEFAULT_VELOCITY = 100
DEFAULT_LIMITS = (-10000, 10000)
DEFAULT_VALUE = 10.124
DEFAULT_WRAP_RANGE = 1

class MotorMockup(AbstractMotor):
    """Mock Motor implementation"""

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.__move_task = None
        self._wrap_range = None

    def init(self):
        """ Initialisation method """
        # get username, actuator_name and tolerance
        AbstractMotor.init(self)

        # local properties
        velocity = self.getProperty("velocity", DEFAULT_VELOCITY)
        self.set_velocity(velocity)

        try:
            wr = self.getProperty("wrap_range", None)
            self._wrap_range = DEFAULT_WRAP_RANGE if not wr else ast.literal_eval(wr)
        except (ValueError, SyntaxError):
            self._wrap_range = DEFAULT_WRAP_RANGE

        try:
            limits = tuple(eval(self.getProperty("default_limits")))
        except TypeError:
            limits = DEFAULT_LIMITS
        self.update_limits(limits)

        default_value = self.getProperty("default_value", DEFAULT_VALUE)
        self.update_value(default_value)

        self.update_state(self.STATES.READY)

    def _move(self, value):
        """ Simulated motor movement
        Args:
            value (float): target position
        """
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
        return value

    def abort(self):
        """Imediately halt movement. By default self.stop = self.abort"""
        if self.__move_task is not None:
            self.__move_task.kill()
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Read the actuator position.
        Returns:
            float: Actuator position.
        """
        return self._nominal_value

    def set_value(self, value, timeout=0):
        """
        Set actuator to absolute value.
        This is NOT the recommended way, but for technical reasons
        overriding is necessary in this particular case
        Args:
            value (float): target value
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait (default);
                             if timeout is None: wait forever.
        Raises:
            ValueError: Value not valid or attemp to set read-only actuator.
        """
        value = value if not self._wrap_range else value % self._wrap_range

        if self.read_only:
            raise ValueError("Attempt to set value for read-only Actuator")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            self.update_specific_state(self.SPECIFIC_STATES.MOVING)
            if timeout or timeout is None:
                with gevent.Timeout(
                    timeout, RuntimeError("Motor %s timed out" % self.username)
                ):
                    self._move(value)
                    self._set_value(value)
            else:
                self.__move_task = gevent.spawn(self._move, value)
                self.__move_task.link(self._callback)
        else:
            raise ValueError("Invalid value %s; limits are %s"
                             % (value, self.get_limits())
                             )

    def _callback(self, move_task):
        value = move_task.get()
        self._set_value(value)

    def _set_value(self, value):
        """
        Implementation of specific set actuator logic.
        Args:
            value (float): target value
        """
        self.update_value(value)
        self.update_state(self.STATES.READY)
        _low, _high = self.get_limits()
        if value == self.default_value:
            self.update_specific_state(self.SPECIFIC_STATES.HOME)
        elif value == _low:
            self.update_specific_state(self.SPECIFIC_STATES.LOWLIMIT)
        elif value == _high:
            self.update_specific_state(self.SPECIFIC_STATES.HIGHLIMIT)
        else:
            self.update_specific_state(None)

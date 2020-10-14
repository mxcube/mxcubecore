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
Mixin superclass for all mock actuators

Should be put as the first superclass,
e.g. class MotorMockup(ActuatorMockup, AbstractMotor):
"""

import time
import random
import gevent
from HardwareRepository.HardwareObjects.abstract import AbstractActuator

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ActuatorMockup(AbstractActuator.AbstractActuator):
    """Mock Motor implementation"""

    def __init__(self, name):
        super(ActuatorMockup, self).__init__(name)
        self.__move_task = None

    def init(self):
        """ Initialisation method """
        super(ActuatorMockup, self).init()
        self.update_state(self.STATES.READY)

    def _move(self, value):
        """ Simulated value change - override as needed

        Must set specific_state as needed, take a non-zero amount of time
        call update_value for intermediate positions
        and return the final value (in case it does not match the input value)

        Args:
            value : target actuator value

        Returns:
            final actuator value (may differ from target value)
        """
        time.sleep(random.uniform(0.1, 1.0))
        return value

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
        if self.read_only:
            raise ValueError("Attempt to set value for read-only Actuator")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            if timeout or timeout is None:
                with gevent.Timeout(
                    timeout, RuntimeError("Motor %s timed out" % self.username)
                ):
                    new_value = self._move(value)
                    self._set_value(new_value)
            else:
                self.__move_task = gevent.spawn(self._move, value)
                self.__move_task.link(self._callback)
        else:
            raise ValueError(
                "Invalid value %s; limits are %s" % (value, self.get_limits())
            )

    def abort(self):
        """Imediately halt movement. By default self.stop = self.abort"""
        if self.__move_task is not None:
            self.__move_task.kill()
        self.update_state(self.STATES.READY)

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

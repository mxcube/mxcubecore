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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Abstract Motor API. Motor states definition"""

import abc
import math
from enum import Enum, unique
from HardwareRepository.BaseHardwareObjects import HardwareObjectState
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class MotorStates(Enum):
    """Motor states definitions."""

    HOME = HardwareObjectState.READY, 5
    LOWLIMIT = HardwareObjectState.READY, 6
    HIGHLIMIT = HardwareObjectState.READY, 7
    MOVING = HardwareObjectState.BUSY, 8


class AbstractMotor(AbstractActuator):
    """Abstract motor API"""

    __metaclass__ = abc.ABCMeta
    unit = None

    SPECIFIC_STATES = MotorStates

    def __init__(self, name):
        AbstractActuator.__init__(self, name)
        self._velocity = None
        self._tolerance = None
        self.specific_state = None

    def init(self):
        """Initialise some parametrs."""
        AbstractActuator.init(self)
        self._tolerance = self.getProperty("tolerance") or 1e-3

    def get_velocity(self):
        """Read motor velocity.
        Returns:
            (float): velocity [unit/s]
        """
        return self._velocity

    def set_velocity(self, velocity):
        """Set the motor velocity
        Args:
            velocity (float): target velocity
        """
        self._velocity = velocity

    def set_value_relative(self, relative_value, timeout=0):
        """
        Set actuator to relative to the current value
        Args:
            value (float): target value
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait;
                             if timeout is None: wait forever.
        """
        self.set_value(self.get_value() + relative_value, timeout)

    def home(self, timeout=None):
        """Homing procedure.
        Args:
            timeout (float): Timeout [s].
        """
        raise NotImplementedError

    def validate_value(self, value):
        """Check if the value is within the limits
        Args:
            value(float): value
        Returns:
            (bool): True if within the limits
        """
        if math.isnan(value) or math.isinf(value):
            return False
        limits = self._nominal_limits
        if None in limits:
            return True
        return limits[0] <= value <= limits[1]

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value (float): value
        """
        if self._nominal_value is None:
            self._nominal_value = self.get_value()

        if value is None:
            value = self.get_value()

        if self._tolerance:
            if abs(value - self._nominal_value) <= self._tolerance:
                return

        self._nominal_value = value
        self.emit("valueChanged", (self._nominal_value,))

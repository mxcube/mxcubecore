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
from enum import IntEnum, unique
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class MotorStates(IntEnum):
    """Motor states definitions."""

    HOME = 5
    LOWLIMIT = 6
    HIGHLIMIT = 7


class AbstractMotor(AbstractActuator):
    """Abstract motor API"""

    __metaclass__ = abc.ABCMeta
    unit = None

    SPECIFIC_STATES = MotorStates

    def __init__(self, name):
        AbstractActuator.__init__(self, name)
        self._velocity = None
        self._tolerance = None

    def init(self):
        """Initialise some parametrs."""
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

    def set_value_relative(self, relative_value, wait=False, timeout=None):
        """Move to value relative to the current. Wait the move to finish.
        Args:
            relative_value (float): relative target value.
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        self.set_value(self.get_value() + relative_value, wait, timeout)

    def home(self, timeout=None):
        """Homing procedure.
        Args:
            timeout (float): Timeout [s].
        """
        raise NotImplementedError

    def update_value(self, value=None):
        """Check if the value has changed. Emist signal valueChanged.
        Args:
            value (float): value
        """
        if self._nominal_value is None:
            self._nominal_value = self.get_value()

        if value is None:
            value = self.get_value()

        if abs(value - self._nominal_value) <= self._tolerance:
            return

        self._nominal_value = value
        self.emit("valueChanged", (self._nominal_value,))

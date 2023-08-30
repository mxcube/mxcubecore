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

""" Mockup shutter implementation"""

from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup


@unique
class ShutterStates(Enum):
    """Shutter states definitions."""

    OPEN = HardwareObjectState.READY, 6
    CLOSED = HardwareObjectState.READY, 7
    MOVING = HardwareObjectState.BUSY, 8
    DISABLED = HardwareObjectState.WARNING, 9
    AUTOMATIC = HardwareObjectState.READY, 10


class ShutterMockup(AbstractShutter, ActuatorMockup):
    """
    ShutterMockup for simulating a simple open/close shutter.
    Fake some of the states of the shutter to correspong to values.
    """

    SPECIFIC_STATES = ShutterStates

    def init(self):
        """Initialisation"""
        super().init()
        self._initialise_values()
        self.update_value(self.VALUES.CLOSED)
        self.update_state(self.STATES.READY)

    def open(self, timeout=0):
        self.set_value(self.VALUES.OPEN, timeout=timeout)

    def close(self, open(self, timeout=0)):
        self.set_value(self.VALUES.CLOSED, timeout=timeout)


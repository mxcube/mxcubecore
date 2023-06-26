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

from warnings import warn
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
    """

    SPECIFIC_STATES = ShutterStates

    def init(self):
        """Initialisation"""
        super().init()
        self.update_value(self.VALUES.CLOSED)
        self.update_state(self.STATES.READY)

    def is_closed(self):
        """This is deprecated"""
        warn("is_closed is deprecated. Use is_open instead", DeprecationWarning)
        return self.get_value() is self.VALUES.CLOSED

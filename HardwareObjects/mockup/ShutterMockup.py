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

import time
import random
from enum import Enum, unique
from HardwareRepository.HardwareObjects.abstract import AbstractNState
# Temporarily, pending a stable AbstactNState:
from HardwareRepository.HardwareObjects.abstract import AbstractActuator


class ShutterMockup(AbstractActuator.AbstractActuator):
    """
    ShutterMockup for simulating a simple open/close shutter.

    TYhis is a temporary vresion, pending a stable AbstractNState
    """

    @unique
    class VALUES(Enum):
        UNKNOWN = "UNKNOWN"
        OPEN = "OPEN"
        CLOSED = "CLOSED"

    def __init__(self, name):
        super(ShutterMockup, self).__init__(name)
        # self.current_state = ShutterMockup.STATE.OPEN

    def init(self):
        super(ShutterMockup, self).init()
        self._nominal_value = getattr(self.VALUES, self.default_value or "UNKNOWN")
        self._state = self.STATES.READY

    def get_value(self):
        return self._nominal_value

    def _set_value(self, value):
        self.update_state(self.STATES.BUSY)
        time.sleep(random.uniform(0.1, 1.0))
        self._nominal_value = value
        self.update_state(self.STATES.READY)

    def validate_value(self, value):
        """This one should be in AbstractNState, just here temporarily"""
        return value in self.VALUES

    def is_open(self):
        return self.get_value() is self.VALUES.OPEN

    def is_closed(self):
        return self.get_value() is self.VALUES.CLOSED

    def open(self):
        self.set_value(self.VALUES.OPEN)

    def close(self):
        self.set_value(self.VALUES.CLOSED)

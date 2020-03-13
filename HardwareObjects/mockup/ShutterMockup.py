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
from HardwareRepository.HardwareObjects.abstract import AbstractNState

class ShutterMockup(AbstractNState.AbstractNState):
    """
    ShutterMockup for simulating a simple open/close shutter. For more detailed
    method documentation see AbstractShutter
    """

    def __init__(self, name):
        AbstractNState.AbstractNState.__init__(self, name)
        # self.current_state = ShutterMockup.STATE.OPEN

    def value_changed(self, value):
        """See AbstractShutter"""
        # self.current_state = ShutterMockup.STATE(value)
        self.emit("shutterStateChanged", self.current_state)

    def getShutterState(self):
        return "opened"

    def is_open(self):
        """See AbstractShutter"""
        return self.current_state == ShutterMockup.STATE.OPEN

    def is_closed(self):
        """See AbstractShutter"""
        return self.current_state == ShutterMockup.STATE.CLOSED

    def is_valid(self):
        """See AbstractShutter"""
        return self.current_state.name in dir(ShutterMockup.STATE)

    def open(self):
        """See AbstractShutter"""
        self.set_state(ShutterMockup.STATE.OPEN)

    def close(self):
        """See AbstractShutter"""
        self.set_state(ShutterMockup.STATE.CLOSED)

    def set_state(self, state, wait=False, timeout=None):
        """See AbstractShutter"""
        time.sleep(random.uniform(0.1, 1.0))
        self.current_state = state
        self.value_changed(state.value)

    def _set_value(self, value):
        return

    def get_value(self):
        return

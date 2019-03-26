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

from abstract.AbstractNState import AbstractShutter
import time
import random


class ShutterMockup(AbstractShutter):
    """
    ShutterMockup for simulating a simple open/close shutter. For more detailed
    method documentation see AbstractShutter
    """

    def __init__(self, name):
        AbstractShutter.__init__(self, name)
        self.current_state = ShutterMockup.STATE.OPEN

    def value_changed(self, value):
        self.current_state = ShutterMockup.STATE(value)
        self.emit("shutterStateChanged", self.current_state.name)

    def state(self):
        return self.current_state.name

    def is_open(self):
        return self.current_state == ShutterMockup.STATE.OPEN

    def is_valid(self):
        return self.current_state.name in dir(ShutterMockup.STATE)

    def open(self):
        self.set_state(ShutterMockup.STATE.OPEN)

    def close(self):
        self.set_state(ShutterMockup.STATE.CLOSED)

    def set_state(self, state, wait=False, timeout=None):
        time.sleep(random.uniform(0.1, 1.0))
        self.current_state = state
        self.value_changed(state.value)

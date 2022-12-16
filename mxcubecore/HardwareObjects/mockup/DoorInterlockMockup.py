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
DoorInterlockMockup
"""

from mxcubecore.BaseHardwareObjects import HardwareObject

__credits__ = ["MXCuBE collaboration"]


class DoorInterlockMockup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.door_interlock_state = None

    def init(self):
        self.door_interlock_state = self.STATES.READY

    def connected(self):
        self.set_is_ready(True)

    def disconnected(self):
        self.set_is_ready(False)

    def door_is_interlocked(self):
        return self.door_interlock_state in [self.STATES.READY]

    def get_state(self):
        return self.door_interlock_state

    def unlock_door_interlock(self):
        if self.door_interlock_state == "locked_active":
            self.door_interlock_state = "unlocked"
        self.emit("doorInterlockStateChanged", self.door_interlock_state, "")
        self.emit("hutchTrigger", self.door_interlock_state == "unlocked")

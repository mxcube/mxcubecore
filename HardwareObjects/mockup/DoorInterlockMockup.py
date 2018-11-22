#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
DoorInterlockMockup
"""

import logging
from HardwareRepository.BaseHardwareObjects import HardwareObject

__credits__ = ["MXCuBE colaboration"]


class DoorInterlockMockup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.door_interlock_state = None

    def init(self):
        self.door_interlock_state = "locked_active"

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def door_is_interlocked(self):
        return self.door_interlock_state in ("locked_active", "locked_inactive")

    def getState(self):
        return self.door_interlock_state

    def unlock_door_interlock(self):
        if self.door_interlock_state == "locked_active":
            self.door_interlock_state = "unlocked"
        self.emit("doorInterlockStateChanged", self.door_interlock_state, "")
        self.emit("hutchTrigger", self.door_interlock_state == "unlocked")

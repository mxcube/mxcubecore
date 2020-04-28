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

from HardwareRepository.HardwareObjects.abstract. AbstractNState import AbstractNState
from HardwareRepository.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup


class ShutterMockup(ActuatorMockup, AbstractNState):
    """
    ShutterMockup for simulating a simple open/close shutter.
    """

    def init(self):
        super(ShutterMockup, self).init()
        self.update_value(self.VALUES.CLOSED)
        self.update_state(self.STATES.READY)

    def is_open(self):
        return self.get_value() is self.VALUES.OPEN

    def is_closed(self):
        return self.get_value() is self.VALUES.CLOSED

    def open(self):
        self.set_value(self.VALUES.OPEN, timeout=None)

    def close(self):
        self.set_value(self.VALUES.CLOSED, timeout=None)

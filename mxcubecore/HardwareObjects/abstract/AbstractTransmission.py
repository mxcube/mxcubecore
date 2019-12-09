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


import abc
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3"


class AbstractTransmission(Device, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        Device.__init__(self, name)

        self._value = None
        self._limits = [0, 100]
        self._state = None

    @abc.abstractmethod
    def set_value(self, value, timeout=None):
        self._value = value
        self.emit("valueChanged", self._value)

    def get_value(self):
        return self._value

    def set_limits(self, limits):
        self._limits = limits
        self.emit("limitsChanged", (self._limits,))

    def get_limits(self):
        return self._limits

    def set_state(self, state):
        self._state = state
        self.emit("stateChanged", self._state)

    def get_state(self):
        return self._state

    def update_values(self):
        self.emit("valueChanged", self._value)
        self.emit("limitsChanged", (self._limits,))
        self.emit("stateChanged", self._state)

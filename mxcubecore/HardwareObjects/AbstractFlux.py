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

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3."
__category__ = "General"


class AbstractFlux(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._value = None
        self._status = None

    def set_flux(self, value):
        self._value = value
        self.emit('fluxValueChanged', self._value)

    def get_flux(self):
        return self._value

    def update_values(self):
        self.emit('fluxValueChanged', self._value)

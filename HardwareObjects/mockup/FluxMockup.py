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

from random import random
from HardwareRepository.HardwareObjects.abstract.AbstractFlux import AbstractFlux


__credits__ = ["MXCuBE collaboration"]
__category__ = "General"


class FluxMockup(AbstractFlux):
    def __init__(self, name):
        AbstractFlux.__init__(self, name)
        self._value = 7e12

    def measure_flux(self):
        """Measures intesity"""
        self._value = 1e12 + random() * 1e12
        self.emit("fluxValueChanged", self._value)

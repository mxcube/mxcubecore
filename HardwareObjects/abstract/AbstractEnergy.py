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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

from HardwareRepository.ConvertUtils import h_over_e

from HardwareRepository.BaseHardwareObjects import HardwareObject


class AbstractEnergy(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._tunable = True
        self._moving = False
        self._aborted = False
        self._default_energy = None
        self._energy_limits = [None, None]
        self._energy_value = None
        self._wavelength_value = None

        self.canMoveEnergy = self.can_move_energy
        self.getEnergyLimits = self.get_energy_limits
        self.getWavelengthLimits = self.get_wavelength_limits
        self.isReady = self.is_ready
        self.getCurrentEnergy = self.get_current_energy
        self.getCurrentWavelength = self.get_current_wavelength

    def is_ready(self):
        return True

    def abort(self):
        self._aborted = True

    def set_tunable(self, state):
        self._tunable = state

    def can_move_energy(self):
        return self._tunable

    def isConnected(self):
        return True

    def set_do_beam_alignment(self, state):
        pass

    def get_current_energy(self):
        return self._energy_value

    def get_current_wavelength(self):
        if self._energy_value is not None:
            return h_over_e / self._energy_value
        else:
            return None

    def get_energy_limits(self):
        return self._energy_limits

    def set_energy_limits(self, limits):
        self._energy_limits = limits

    def get_wavelength_limits(self):
        lims = None
        if self._energy_limits is not None:
            lims = (
                h_over_e / self._energy_limits[1],
                h_over_e / self._energy_limits[0],
            )
        return lims

    def move_energy(self, value, wait=True):
        self._energy_value = value
        self.update_values()

    def move_wavelength(self, value, wait=True):
        self.move_energy(h_over_e / value, wait)

    def update_values(self):
        self.emit("energyChanged", self._energy_value, h_over_e / self._energy_value)

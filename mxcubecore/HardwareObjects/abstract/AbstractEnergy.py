# -*- coding: utf-8 -*-
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

"""Abstract Energy API"""

from scipy.constants import h, c, e
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import MotorStates

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

class AbstractEnergy(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.tunable = True
        self.state = None
        self._aborted = False
        self._default_energy = None
        self.energy_limits = ()
        self._wavelength_limits = ()
        self._energy_value = None
        self._wavelength_value = None

    def is_ready(self):
        """Check if the motor state is READY.
        Returns:
            (bool): True if ready, otherwise False.
        """
        if self.tunable:
            return True
        return MotorStates.READY in self.state

    def abort(self):
        self._aborted = True

    def set_tunable(self, state):
        self.tunable = state

    def get_current_energy(self):
        return self.get_energy()
    
    def get_energy(self):
        """Read the energy
        Returns:
            (float): Energy [keV]
        """
        return self._energy_value

    def get_wavelength(self):
        """Read the wavelength
        Returns:
            (float): Wavelength [Å]
        """
        if not self._wavelength_value:
            if self._energy_value:
                self._wavelength_value = self._calculate_wavelength(
                    self._energy_value)
        return self._wavelength_value

    def get_limits(self):
        """Return energy and wavelength low and high limits.
        Returns:
            (tuple): tuple of two floats tuple (low limit, high limit).
        """
        if not self._wavelength_limits:
            self.get_wavelength_limits()
        return self._energy_limits, self._wavelength_limits

    def get_energy_limits(self):
        """Return energy low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        return self._energy_limits

    def get_wavelength_limits(self):
        """Return wavelength low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        if not self._wavelength_limits:
            _low, _high = self._energy_limits
            self._wavelength_limits = (self._calculate_wavelength(_low),
                                      self._calculate_wavelength(_high))
        return self._wavelength_limits

    def move_energy(self, value, wait=True, timeout=None):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target position [keV]
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """

    def move_wavelength(self, value, wait=True):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target position [keV]
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
    def _calculate_wavelength(self, energy=None):
        """Calculate wavelength from energy
        Args:
            energy(float): Energy [keV]
        Returns:
            (float): wavelength [Å]
        """
        hc_over_e = h * c / e * 10e6
        energy = energy or self._energy_value

        # energy in KeV to get wavelength in Å
        energy = energy / 1000.0 if energy > 1000 else energy

        return hc_over_e / energy

    def _calculate_energy(self, wavelength=None):
        """Calculate energy from wavelength
        Args:
            value((float): wavelength [Å]
        Returns:
            (float): Energy [keV]
        """
        hc_over_e = h * c / e * 10e6
        wavelength = wavelength or self._wavelength_value
        return  hc_over_e / wavelength
    
    def update_state(self, state):
        """Emist signal stateChanged.
        Args:
            state (enum 'MotorState'): state
        """
        self.emit("stateChanged", (state,))

    def update_values(self):
        """Emist signal energyChanged for both energy and wavelength"""
        if not self._wavelength_value:
            self._wavelength_value = self._calculate_wavelength(self._energy_value)
        self.emit("energyChanged", self._energy_value, self._wavelength_value)

        

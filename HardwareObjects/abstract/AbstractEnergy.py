# -*- coding: utf-8 -*-
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Abstract Energy and Wavelength"""

import abc
import math
from scipy.constants import h, c, e
from mx3core.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractEnergy(AbstractActuator):
    """Abstract Energy and Wavelength"""

    # Unit for 'value' attribute
    unit = "keV"

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        AbstractActuator.__init__(self, name)
        self._wavelength_value = None
        self._wavelength_limits = (None, None)

    def is_ready(self):
        """Check if the state is ready.
        Returns:
            (bool): True if ready, False otherwise.
        """
        if self.read_only:
            return True
        return super(AbstractEnergy, self).is_ready()

    @property
    def is_tunable(self):
        """Check if not fixed energy.
        Returns:
            (bool): True if tunable, False if fixed energy.
        """
        return not self.read_only

    def get_wavelength(self):
        """Read the wavelength
        Returns:
            (float): Wavelength [Å].
        """
        self._wavelength_value = self._calculate_wavelength(self.get_value())
        return self._wavelength_value

    def get_wavelength_limits(self):
        """Return wavelength low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit) [Å].
        """
        _low, _high = self.get_limits()
        self._wavelength_limits = (
            self._calculate_wavelength(_high),
            self._calculate_wavelength(_low),
        )
        return self._wavelength_limits

    def set_wavelength(self, value, timeout=None):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target position [keV]
            timeout (float): optional - timeout [s].
                             if timeout = 0: return at once and do not wait
                             if timeout is None: wait forever
        """
        self.set_value(self._calculate_energy(value), timeout=timeout)

    def _calculate_wavelength(self, energy=None):
        """Calculate wavelength from energy
        Args:
            energy(float): Energy [keV]
        Returns:
            (float): wavelength [Å]
        """
        hc_over_e = h * c / e * 10e6
        energy = energy or self.get_value()

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
        return hc_over_e / wavelength

    def validate_value(self, value):
        """Check if the value is within the limits
        Args:
            value(float): value
        Returns:
            (bool): True if within the limits
        """
        if value is None:
            return True
        if math.isnan(value) or math.isinf(value):
            return False
        limits = self.get_limits()
        if None in limits:
            return True
        return limits[0] <= value <= limits[1]

    def get_undulator_gaps(self):
        """Returns undulator gaps

        Returns:
            list: undulator gaps in mm as a list of floats
        """
        return ()

    def force_emit_signals(self):
        """Emits signal energyChanged for both energy and wavelength
        Argin:
            value: Not used, but kept in the method signature.
        """
        AbstractActuator.force_emit_signals(self)
        self.emit("wavelengthChanged", self.get_wavelength())

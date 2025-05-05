#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
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
"""
Energy and Wavelength with bliss.
Example yaml file:
- for tunable wavelength beamline:
.. code-block:: yaml

 class: BlissEnergy.BlissEnergy
 configuration:
   username: Energy
 objects:
   controller: bliss.yml
   energy_motor: energy_motor.yml

- for fixed wavelength beamline:
.. code-block:: yaml

 class: BlissEnergy.BlissEnergy
 configuration:
   username: Energy
   read_only: True
   default_value: 12.8123

"""

import logging
import math

from gevent import spawn

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissEnergy(AbstractEnergy):
    """Energy and Wavelength with bliss."""

    def __init__(self, name):
        super().__init__(name)
        self.energy_motor = None
        self.controller = None
        self._cmd_execution = None

    def init(self):
        """Initialisation"""
        super().init()

        self.controller = self.get_object_by_role("controller")
        self.energy_motor = self.get_object_by_role("energy_motor")
        self.update_state(HardwareObjectState.READY)

        if self.energy_motor:
            self.update_state(self.energy_motor.get_state())
            self.energy_motor.connect("valueChanged", self.update_value)
            self.energy_motor.connect("stateChanged", self.update_state)

        if self.read_only and not self.energy_motor:
            # self._nominal_value = float(self.get_property("energy", 0))
            try:
                self._nominal_value = float(self.default_value)
            except TypeError as err:
                msg = "Energy not defined"
                raise RuntimeError(msg) from err

    def get_value(self):
        """Read the energy.
        Returns:
            (float): Energy [keV]
        """
        if self.energy_motor:
            self._nominal_value = self.energy_motor.get_value()
        return self._nominal_value

    def get_limits(self):
        """Return energy low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit) [keV].
        """
        if not self.read_only:
            self._nominal_limits = self.energy_motor.get_limits()
        return self._nominal_limits

    def stop(self):
        """Stop the energy motor movement"""
        self.energy_motor.stop()

    def _set_value(self, value):
        """Execute the sequence to move to an energy
        Args:
            value (float): target energy
        """
        self.update_state(HardwareObjectState.BUSY)
        try:
            self.controller.change_energy(value)
        except (AttributeError, RuntimeError):
            self.energy_motor.set_value(value)
        self.update_state(HardwareObjectState.READY)

    def set_value(self, value, timeout=0):
        """Move energy to absolute position. Wait the move to finish.
        Args:
            value (float): target value.
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                             if timeout is None: wait forever.
        Raises:
            ValueError: Value not valid or attemp to set write only actuator.
        """
        if self.read_only:
            return

        if self.validate_value(value):
            current_value = self.get_value()

            _delta = math.fabs(current_value - value)
            if _delta < 0.001:
                logging.getLogger("user_level_log").info(
                    "Energy: already at %g, not moving", value
                )
                return

            logging.getLogger("user_level_log").info(
                "Energy: moving energy to %g", value
            )

            if _delta > 0.02:
                if timeout:
                    self._set_value(value)
                else:
                    self._cmd_execution = spawn(self._set_value(value))
            else:
                self.energy_motor.set_value(value, timeout=timeout)
        else:
            msg = f"Invalid value {value}"
            raise ValueError(msg)

    def abort(self):
        """Abort the procedure"""
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

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
Example xml file:
  - for tunable wavelength beamline:
<object class="Energy">
  <object href="/energy" role="energy_motor"/>
  <object href="/bliss" role="bliss"/>
</object>
The energy should have methods get_value, get_limits and move.
If used, the controller should have method moveEnergy.

  - for fixed wavelength beamline:
<object class="Energy">
  <read_only>True</read_only>
  <energy>12.8123</energy>
</object>
"""
import logging
import math
from gevent import spawn
from mx3core.hardware_objects.abstract.AbstractEnergy import AbstractEnergy
from mx3core.BaseHardwareObjects import HardwareObjectState

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissEnergy(AbstractEnergy):
    """Energy and Wavelength with bliss."""

    def __init__(self, name):
        AbstractEnergy.__init__(self, name)
        self._energy_motor = None
        self._bliss_session = None
        self._cmd_execution = None

    def init(self):
        """Initialisation"""
        AbstractEnergy.init(self)
        self._energy_motor = self.get_object_by_role("energy_motor")
        self._bliss_session = self.get_object_by_role("bliss")
        self.update_state(HardwareObjectState.READY)

        if self._energy_motor:
            self.update_state(self._energy_motor.get_state())
            self._energy_motor.connect("valueChanged", self.update_value)
            self._energy_motor.connect("stateChanged", self.update_state)

        if self.read_only:
            self._nominal_value = float(self.get_property("energy", 0))

    def get_value(self):
        """Read the energy.
        Returns:
            (float): Energy [keV]
        """
        if not self.read_only:
            self._nominal_value = self._energy_motor.get_value()
        return self._nominal_value

    def get_limits(self):
        """Return energy low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit) [keV].
        """
        if not self.read_only:
            self._nominal_limits = self._energy_motor.get_limits()
        return self._nominal_limits

    def stop(self):
        """Stop the energy motor movement"""
        self._energy_motor.stop()

    def _set_value(self, value):
        """Execute the sequence to move to an energy
        Args:
            value (float): target energy
        """
        try:
            self._bliss_session.change_energy(value)
        except RuntimeError:
            self._energy_motor.set_value(value)

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
                logging.getLogger("user_level_log").debug(
                    "Energy: already at %g, not moving", value
                )
                return

            logging.getLogger("user_level_log").debug(
                "Energy: moving energy to %g", value
            )

            if _delta > 0.02:
                if timeout:
                    self._set_value(value)
                else:
                    self._cmd_execution = spawn(self._set_value(value))
            else:
                self._energy_motor.set_value(value, timeout=timeout)
        else:
            raise ValueError("Invalid value %s" % str(value))

    def abort(self):
        """Abort the procedure"""
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def set_wavelength(self, value, timeout=None):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target position [Å]
            timeout (float): optional - timeout [s].
                             if timeout = 0: return at once and do not wait
                             if timeout is None: wait forever
        """

        value = self._calculate_energy(value)
        self.set_value(value, timeout)

    def validate_value(self, value):
        """Check if the value is within the limits
        Args:
            value(float): value
        Returns:
            (bool): True if within the limits
        """
        limits = self._nominal_limits
        if None in limits:
            return True
        return limits[0] <= value <= limits[1]

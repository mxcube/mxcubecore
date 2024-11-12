# encoding: utf-8
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
"""
Example xml file:
<device class="MotorMockupBis">
  <username>Detector Distance</username>
  <actuator_name>dtox</actuator_name>
  <tolerance>1e-2</tolerance>
</device>
"""

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MotorMockupBis(AbstractMotor):
    """Motor Motor implementation"""

    def init(self):
        """Initialise the motor"""
        super().init()
        # init state to match motor's one
        self.update_state(self.STATES.READY)

    def get_state_nu(self):
        """Get the motor state.
        Returns:
            (enum HardwareObjectState): Motor state.
        """
        return HardwareObjectState.READY

    def get_value(self):
        return self._nominal_value

    def _set_value(self, value):
        """Move motor to absolute value.
        Args:
            value (float): target value
        """
        self.update_state(self.STATES.BUSY)
        # self.update_value(value)
        self._nominal_value = value
        self.update_state(self.STATES.READY)

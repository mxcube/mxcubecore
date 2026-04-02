# encoding: utf-8
#
#  Project name: MXCuBE
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
Wago module, interfaced as a motor, e.g. used to control the backlight level.

Example yml configuration:

.. code-block:: yaml

 class: BlissWagoMotor.BlissWagoMotor
 configuration:
   actuator_name: wcid29cb
   channel_name: lightctrl
   username: Backlight Level
   default_limits: [0, 10]

"""

from bliss.config import static

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissWagoMotor(AbstractMotor):
    """Wago module, interfaced as a motor"""

    def __init__(self, name):
        super().__init__(name)
        self.wago = None
        self.channel_name = None

    def init(self):
        """Initialise the wago and its channel"""
        super().init()
        self.wago = static.get_config().get(self.actuator_name)
        self.channel_name = self.get_property("channel_name", "lightctrl")
        self.update_state(self.STATES.READY)

    def _set_value(self, value: float):
        """Move motor to absolute value.
        Args:
            value:  target value
        """
        self.wago.set(self.channel_name, value)

    def get_value(self) -> float:
        """Read the value.
        Returns:
            The value.
        """
        return self.wago.get(self.channel_name)

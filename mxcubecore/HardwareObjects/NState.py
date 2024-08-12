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
Concrete Implementation of AbstartNState - overloads the get_value
and _set_value abstract methods.
Example xml configuration:

.. code-block:: xml

 <object class="NState">
   <username>Beam Monitoring</username>
   <actuator_name>beam_monitor</actuator_name>
   <values>{"ENABLED": True, "DISABLED": False}</values>
 </object>
"""
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class NState(AbstractNState):
    """Overload get_value and _set_value abstract methods"""

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): VALUES Enum member
        """
        return self._nominal_value

    def _set_value(self, value):
        """Set the value.
        Args:
            value (Enum): target value
        """
        self.update_value(value)

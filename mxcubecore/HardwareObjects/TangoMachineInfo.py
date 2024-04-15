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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""MachineInfo using Tango channels.

Example xml_ configuration:

.. code-block:: xml

 <object class="TangoMachineInfo">
   <tangoname>ab/cd/ef</tangoname>
   <parameters>["current", "lifetime", "message", "refill_countdown"]</parameters>
   <channel type="tango" name="current" polling="2000">SR_Current</channel>
   <channel type="tango" name="lifetime" polling="2000">SR_Lifetime</channel>
   <channel type="tango" name="refill_countdown" polling="2000">SR_Refill_Countdown</channel>
   <channel type="tango" name="message" polling="8000">SR_Operator_Mesg</channel>
 </object>
"""

import logging
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class TangoMachineInfo(AbstractMachineInfo):
    """MachineInfo using Tango channels."""

    def init(self):
        """We assume that at least current is defined"""
        super().init()
        # we only consider the attributes defined in the parameters property
        for name in self._mach_info_keys:
            if hasattr(self.get_channel_object(name), "get_value"):
              setattr(self, f"{name}", self.get_channel_object(name))
            else:
                # remove the attributes we cannot read
                self._mach_info_keys.pop(name)

        # we only want to update when the current changes.
        self.current.connect_signal("update", self._update_value)
        self.update_state(self.STATES.READY)

    def _check_attributes(self, attr_list=None):
        """Check if all the keys in the configuration file have
        implemented read method. Remove the undefined.
        """
        attr_list = attr_list or self._mach_info_keys

        for attr_key in attr_list:
            try:
               hasattr(self.get_channel_object(attr_key), "get_value")
            except AttributeError:
                attr_list.remove(attr_key)
        self._mach_info_keys = attr_list

    def _update_value(self, value):
        """Update all the attributes, not only the current."""
        self.update_value()

    def get_value(self) -> dict:
        """Read machine info summary as dictionary.

        Returns:
            Copy of the _mach_info_dict.
        """
        for name in self._mach_info_keys:
            try:
                self._mach_info_dict.update({name: getattr(self, name).get_value()})
            except Exception as err:
                logging.getLogger("HWR").exception(err)

        return self._mach_info_dict.copy()

    def get_current(self) -> float:
        """Read the ring current.

        Returns:
            Current [mA].
        """
        return self.current.get_value()

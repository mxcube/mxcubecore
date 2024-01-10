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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

""" TangoShutter class - interface for shutter controlled by TANGO
Implements _set_value, get_value methods
Tango states are: UNKNOWN, OPEN, CLOSED, FAULT
"MOVING", "DISABLE", "STANDBY", "RUNNING"
Example xml file:
<object class = "TangoShutter">
  <username>Safety Shutter</username>
  <tangoname>ab/cd/ef</tangoname>
  <command type="tango" name="Open">Open</command>
  <command type="tango" name="Close">Close</command>
  <channel type="tango" name="State" polling="1000">State</channel>
</object>
"""
from enum import Enum, unique
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter

from mxcubecore.BaseHardwareObjects import HardwareObjectState

__copyright__ = """ Copyright © 2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class TangoShutterStates(Enum):
    """Shutter states definitions."""
    CLOSED = HardwareObjectState.READY, "CLOSED"
    OPEN = HardwareObjectState.READY, "OPEN"
    MOVING = HardwareObjectState.BUSY, "MOVING"
    DISABLE = HardwareObjectState.WARNING, "DISABLE"
    AUTOMATIC = HardwareObjectState.READY, "RUNNING"
    UNKNOWN = HardwareObjectState.UNKNOWN, "RUNNING"
    FAULT = HardwareObjectState.WARNING, "FAULT"


class TangoShutter(AbstractShutter):
    """TANGO implementation of AbstractShutter"""

    SPECIFIC_STATES = TangoShutterStates

    def __init__(self, name):
        AbstractShutter.__init__(self, name)
        self.open_cmd = None
        self.close_cmd = None
        self.state_channel = None

    def init(self):
        """Initilise the predefined values"""
        AbstractShutter.init(self)
        self.open_cmd = self.get_command_object("Open")
        self.close_cmd = self.get_command_object("Close")
        self.state_channel = self.get_channel_object("State")

        """Get the values dict from the xml config file. It will be used to map specific state values to existing standard states defined """
        self.properties_dict = eval(f'dict( {self.get_property("values")} )')

        self._initialise_values()
        self.state_channel.connect_signal("update", self._update_value)
        self.update_state()

    def _update_value(self, value):
        """Update the value.
        Args:
            value(str): The value reported by the state channel.
        """
        value = self.properties_dict[value.name]
        super().update_value(self.value_to_enum(value))
        
    def _initialise_values(self):
        """Add the tango states to VALUES"""
        values_dict = {item.name: item.value for item in self.VALUES}
        values_dict.update(
            {
                "MOVING": "MOVING",
                "DISABLE": "DISABLE",
                "STANDBY": "STANDBY",
                "FAULT": "FAULT",
            }
        )
        self.VALUES = Enum("ValueEnum", values_dict)

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        try:
            _state = self.properties_dict[self.state_channel.get_value().name] 
        except (AttributeError, KeyError):
            return self.STATES.UNKNOWN
        return self.SPECIFIC_STATES[_state].value[0]

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        _val = self.properties_dict[self.state_channel.get_value().name]
       	return self.value_to_enum(_val)

    def _set_value(self, value):
        if value.name == "OPEN":
            self.open_cmd()
        elif value.name == "CLOSED":
            self.close_cmd()

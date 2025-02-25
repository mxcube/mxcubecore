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

"""TangoShutter class - interface for shutter controlled by TANGO
Implements _set_value, get_value methods

Tango states are:
"UNKNOWN", "OPEN", "CLOSED", "FAULT", "MOVING", "DISABLE", "STANDBY", "RUNNING"

Example xml file:

.. code-block:: xml

 <object class = "TangoShutter">
   <username>Safety Shutter</username>
   <tangoname>ab/cd/ef</tangoname>
   <command type="tango" name="Open">Open</command>
   <command type="tango" name="Close">Close</command>
   <channel type="tango" name="State" polling="1000">State</channel>
   <values>{"OPEN": "MYOPEN", "NEWSTATE": ["MYSTATE", "BUSY"]}</values>
 </object>

In the example the <values> property contains a dictionary that redefines or
adds specific tango shutter states.
When redefining a known state, only the VALUES Enum will be updated.
When defining a new state (new key), the dictionary value should be a
list. The new state is added to both the ``VALUES`` and the ``SPECIFIC_STATES`` enumeration.

Attention:

- do not use tuples or the Python JSON parser will fail!
- make sure only double quotes (``"``) are used inside the values dictionary,
  no single quotes (``'``) are allowed!
- the second element of the list should be a standard ``HardwareObjectState`` name
  (``UNKNOWN``, ``WARNING``, ``BUSY``, ``READY``, ``FAULT``, or ``OFF``;
  see in ``BaseHardwareObjects``)!

The ``<values>`` property is optional.
"""

import json
import logging
from enum import (
    Enum,
    unique,
)

from tango import DevState

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

hwr_logger = logging.getLogger("HWR")


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
    STANDBY = HardwareObjectState.WARNING, "STANDBY"


class TangoShutter(AbstractShutter):
    """TANGO implementation of AbstractShutter"""

    SPECIFIC_STATES = TangoShutterStates

    def __init__(self, name: str):
        super().__init__(name)
        self.open_cmd = None
        self.close_cmd = None
        self.state_channel = None

    def init(self) -> None:
        """Initialise the predefined values"""
        super().init()
        self.open_cmd = self.get_command_object("Open")
        self.close_cmd = self.get_command_object("Close")
        self.state_channel = self.get_channel_object("State")
        self._initialise_values()
        self.state_channel.connect_signal("update", self._update_value)
        self.update_state()

    def _update_value(self, value: DevState | str) -> None:
        """Update the value.

        Args:
            value: The value reported by the state channel.
        """
        super().update_value(self.value_to_enum(str(value)))

    def _initialise_values(self) -> None:
        """Add specific tango states to VALUES and, if configured
        in the xml file, to SPECIFIC_STATES"""
        values_dict = {item.name: item.value for item in self.VALUES}
        states_dict = {item.name: item.value for item in self.SPECIFIC_STATES}
        values_dict.update(
            {
                "MOVING": "MOVING",
                "DISABLE": "DISABLE",
                "STANDBY": "STANDBY",
                "FAULT": "FAULT",
            }
        )
        try:
            config_values = json.loads(self.get_property("values"))
            for key, val in config_values.items():
                if isinstance(val, (tuple, list)):
                    values_dict.update({key: val[1]})
                    states_dict.update({key: (HardwareObjectState[val[1]], val[0])})
                else:
                    values_dict.update({key: val})
        except (ValueError, TypeError):
            hwr_logger.exception("Exception in _initialise_values()")

        self.VALUES = Enum("ValueEnum", values_dict)
        self.SPECIFIC_STATES = Enum("TangoShutterStates", states_dict)

    def get_state(self) -> HardwareObjectState:
        """Get the device state.

        Returns:
            Device state.
        """
        try:
            _state = self.get_value().name
            return self.SPECIFIC_STATES[_state].value[0]
        except (AttributeError, KeyError):
            hwr_logger.exception("Exception in get_state()")
            return self.STATES.UNKNOWN

    def get_value(self) -> TangoShutterStates:
        """Get the device value

        Returns:
            Enum member, corresponding to the 'VALUE' or UNKNOWN.
        """
        _val = str(self.state_channel.get_value())
        return self.value_to_enum(_val)

    def _set_value(self, value: TangoShutterStates) -> None:
        if value.name == "OPEN":
            self.open_cmd()
        elif value.name == "CLOSED":
            self.close_cmd()

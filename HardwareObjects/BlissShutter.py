# encoding: utf-8
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

""" BlissShutter class - interface for shutter controlled by BLISS
Implements _set_value, get_value methods
Bliss states are: UNKNOWN, OPEN, CLOSED, FAULT
"MOVING", "DISABLE", "STANDBY", "RUNNING"
Example xml file:
<devic class="BlissShutter">
  <username>Safety Shutter</username>
  <name>safshut</name>
  <type>tango</type>
  <object href="/bliss" role="controller"/>
</device>
"""

from enum import Enum, unique
from HardwareRepository.HardwareObjects.abstract.AbstractShutter import AbstractShutter

from HardwareRepository.BaseHardwareObjects import HardwareObjectState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class BlissShutterStates(Enum):
    """Shutter states definitions."""

    OPEN = HardwareObjectState.READY, "OPEN"
    CLOSED = HardwareObjectState.READY, "CLOSED"
    MOVING = HardwareObjectState.BUSY, "MOVING"
    DISABLED = HardwareObjectState.WARNING, "DISABLED"
    AUTOMATIC = HardwareObjectState.READY, "RUNNING"
    UNKNOWN = HardwareObjectState.UNKNOWN, "RUNNING"
    FAULT = HardwareObjectState.WARNING, "FAULT"


class BlissShutter(AbstractShutter):
    """BLISS implementation of AbstractShutter """

    SPECIFIC_STATES = BlissShutterStates

    def __init__(self, name):
        AbstractShutter.__init__(self, name)
        self._bliss_obj = None
        self.shutter_type = None
        self.opening_mode = None

    def init(self):
        """Initilise the predefined values"""
        AbstractShutter.init(self)
        _name = self.getProperty("name")
        self._bliss_obj = getattr(self.getObjectByRole("controller"), _name)
        # for now we only treat tango type shutter
        self.shutter_type = self.getProperty("type", "tango")
        try:
            if self._bliss_obj.frontend:
                self.opening_mode = self._bliss_obj.mode
        except AttributeError:
            # there is no frontend property
            pass
        if self.shutter_type == "tango":
            self._initialise_values()

    def _initialise_values(self):
        """ Add the tango states to VALUES"""
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
            _state = self._bliss_obj.state.name
        except (AttributeError, KeyError):
            return self.STATES.UNKNOWN
        return self.SPECIFIC_STATES[_state].value[0]

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        # the return from BLISS value is an Enum
        _val = self._bliss_obj.state.name
        self._nominal_value = self.value_to_enum(_val)
        return self._nominal_value

    def _set_value(self, value):
        if value.name == "OPEN":
            self._bliss_obj.open()
        elif value.name == "CLOSED":
            self._bliss_obj.close()

    def set_mode(self, value):
        """Set automatic or manual mode for a Frontend shutter
        Args:
            value (str): MANUAL or AUTOMATIC
        Raises: NotImplementedError: Not a Fronend shutter.
        """
        self._bliss_obj.mode = value
        self.opening_mode = value

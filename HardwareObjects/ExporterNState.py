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
Microdiff with Exporter implementation of AbstartNState
Example xml file:
<device class="ExporterNState">
  <username>Fluorescence Detector</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <value_channel_name>FluoDetectorIsBack</value_channel_name>
  <state_channel_name>State</state_channel_name>
  <values>{"IN": False, "OUT": True}</values>
</device>
"""
from enum import Enum
from mx3core.HardwareObjects.abstract.AbstractNState import AbstractNState
from mx3core.BaseHardwareObjects import HardwareObjectState
from mx3core.Command.Exporter import Exporter
from mx3core.Command.exporter.ExporterStates import ExporterStates

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ExporterNState(AbstractNState):
    """Microdiff with Exporter implementation of AbstartNState"""

    SPECIFIC_STATES = ExporterStates

    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self._exporter = None
        self.value_channel = None
        self.state_channel = None

    def init(self):
        """Initialise the device"""
        AbstractNState.init(self)
        value_channel = self.get_property("value_channel_name")
        state_channel = self.get_property("state_channel_name", "State")

        _exporter_address = self.get_property("exporter_address")
        _host, _port = _exporter_address.split(":")
        self._exporter = Exporter(_host, int(_port))

        self.value_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": value_channel.lower(),
            },
            value_channel,
        )
        self.value_channel.connect_signal("update", self.update_value)

        self.state_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "state",
            },
            state_channel,
        )

        self.state_channel.connect_signal("update", self._update_state)
        self.update_state()

    def _update_state(self, state=None):
        """To be used to update the state when emiting the "update" signal.
        Args:
            state (str): optional state value
        Returns:
            (enum 'HardwareObjectState'): state.
        """
        if not state:
            state = self.get_state()
        else:
            state = self._value2state(state)
        return self.update_state(state)

    def _value2state(self, state):
        """Convert string state to HardwareObjectState enum value
        Args:
            state (str): the state
        Returns:
            (enum 'HardwareObjectState'): state
        """
        try:
            return self.SPECIFIC_STATES.__members__[state.upper()].value
        except (AttributeError, KeyError):
            return self.STATES.UNKNOWN

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        state = self.state_channel.get_value()
        return self._value2state(state)

    def abort(self):
        """Stop the action."""
        if self.get_state() != self.STATES.UNKNOWN:
            self._exporter.execute("abort")

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        # NB Workaround beacuse diffractomer does not send event on
        # change of light position
        self.update_state(self.STATES.BUSY)

        if isinstance(value, Enum):
            if isinstance(value.value, tuple) or isinstance(value.value, list):
                value = value.value[0]
            else:
                value = value.value

        self.value_channel.set_value(value)
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        _val = self.value_channel.get_value()
        return self.value_to_enum(_val)

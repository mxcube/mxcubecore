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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""
Microdiff with Exporter implementation of AbstartNState
Example xml file:
<device class="ExporterNState">
  <username>Fluorescence Detector</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <cmd_name>FluoDetectorIsBack</cmd_name>
  <state_definition>InOutEnum</state_definition>
</device>
"""
from gevent import Timeout, sleep
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState
from HardwareRepository.Command.Exporter import Exporter
from HardwareRepository.Command.exporter.ExporterStates import ExporterStates

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
        value_channel = self.getProperty("value_channel_name")
        state_channel = self.getProperty("state_channel_name")

        _exporter_address = self.getProperty("exporter_address")
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
        self.value_channel.connectSignal("update", self.update_value)

        self.state_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "state",
            },
            state_channel,
        )
 
        self.state_channel.connectSignal("update", self._update_state)
        self.update_state()

    def _update_state(self, state):
        return self.update_state(self.get_state(state))

    def get_state(self, state=None):
        if not state:
            state = self.state_channel.get_value()

        try:
            state = state.upper()
            state = ExporterStates.__members__[state].value
        except (AttributeError, KeyError):
            state = self.STATES.UNKNOWN
       
        return state

    def abort(self):
        """Stop the action."""
        if self.get_state() != self.STATES.UNKNOWN:
            self._exporter.execute("abort")

    def _set_value(self, enum_var):
        """Set device to value of enum_var

        Args:
            value (enum): enum variable
        """
        self.value_channel.set_value(enum_var.value)
        self.update_state()

    def get_value(self):
        """Get the device value
        Returns:
            (str): The name of the enum variable
        """
        _val = self.value_channel.get_value()
        value = self.VALUES.UNKNOWN

        for enum_var in self.VALUES.__members__.values():
            if enum_var.value == _val:
                value = enum_var

        return value
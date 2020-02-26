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
  <predefined_value>
      <name>IN</name>
      <value>True</value>
  </predefined_value>
  <predefined_value>
      <name>OUT</name>
      <value>False</value>
  </predefined_value>
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
        value_channel = self.getProperty("cmd_name")

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
            "State",
        )
        # check if the state is State or HardwareState
        if self.state_channel:
            self.state_channel.connectSignal("update", self._update_state)

    def _ready(self):
        """Get the "Ready" state - software and hardware.
        Returns:
            (bool): True if both "Ready", False otherwise.
        """
        _sw = self.state_channel.get_value() == "Ready"
        try:
            _hw = self._exporter.read_property("HardwareState") == "Ready"
        except AttributeError:
            _hw = True

        return all((_sw, _hw))

    def _wait_ready(self, timeout=None):
        """Wait for the state to be "Ready".
        Args:
            timeout (float): waiting time [s],
                             If timeout == 0: return at once and do not wait;
                             if timeout is None: wait forever.
        Raises:
            RuntimeError: Execution timeout.
        """
        with Timeout(timeout, RuntimeError("Execution timeout")):
            while not self._ready():
                sleep(0.01)

    def validate_value(self, value, limits=None):
        """Check if the value is in the list of predefined values
        Args:
            value: Current value
        Returns:
            (bool): True/False
        """
        if not limits:
            limits = tuple(self.predefined_values.values())
        return value in limits

    def _update_state(self, state):
        if not state:
            state = self.get_state()
        else:
            state = self._value2state(state)
        return self.update_state(state)

    def _value2state(self, state):
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
        """Set device to value.
        Args:
            value (str): target value
        """
        self.value_channel.set_value(self.predefined_values[value])

    def get_value(self):
        """Get the device value
        Returns:
            (str): The value or "unknown"
        """
        _val = self.value_channel.get_value()
        try:
            _key = [key for key, val in self.predefined_values.items() if val == _val][
                0
            ]
        except IndexError:
            _key = "unknown"
        return _key

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
  <value_channel_name>FluoDetectorIsBack</value_channel_name>
  <state_channel_name>State</state_channel_name>
  <values>{"IN": False, "OUT": True}</values>
</device>
"""
from enum import Enum
from gevent import Timeout, sleep
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.Command.Exporter import Exporter
from mxcubecore.Command.exporter.ExporterStates import ExporterStates

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

class ExporterNStateMockup(AbstractNState):
    """Microdiff with Exporter implementation of AbstartNState"""

    SPECIFIC_STATES = ExporterStates

    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self._mock_value = "OUT"
        self._mock_state= "READY"
        
    def init(self):
        """Initialise the device"""
        AbstractNState.init(self)
        self.update_state(self.STATES.READY)

    def _wait_ready(self, timeout=None):
        """Wait timeout seconds till status is ready.
        Args:
            timeout(float): Timeout [s]. None means infinite timeout.
        """
        sleep(0.5)

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
            state = self._str2state(state)

            return self.update_state(state)

    def _str2state(self, state):
        """Convert string state to HardwareObjectState enum value.
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
        return self._str2state(self._mock_state)

    def abort(self):
        """Stop the action."""
        pass

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        self.update_state(self.STATES.BUSY)

        sleep(0.5)

        if isinstance(value, Enum):
            if isinstance(value.value, (tuple, list)):
                value = value.value[0]
            else:
                value = value.value

        self._mock_value = value
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        _val = self._mock_value
        return self.value_to_enum(_val)

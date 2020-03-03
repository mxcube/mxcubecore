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
bliss implementation of AbstartNState
Example xml file:
<device class="BlissNState">
  <username>Detector Cover</username>
  <object_name>detcover</>
  <object href="/bliss" role="controller"/>
  <predefined_value>
      <name>in</name>
      <value>IN</value>
  </predefined_value>
  <predefined_value>
      <name>out</name>
      <value>OUT</value>
  </predefined_value>
</device>
"""

from gevent import Timeout, sleep
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import MotorStates
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissNState(AbstractNState):
    """bliss implementation of AbstartNState"""

    SPECIFIC_STATES = MotorStates

    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self._bliss_obj = None
        self.device_type = None
        self.__saved_state = None

    def init(self):
        """Initialise the device"""
        AbstractNState.init(self)
        _name = self.getProperty("object_name")
        self._bliss_obj = getattr(self.getObjectByRole("controller"), _name)

        self.device_type = "actuator"
        if "MultiplePositions" in self._bliss_obj.__class__:
            self.device_type = "motor"

        if self.device_type == "actuator":
            self.connect(self.bliss_obj, "state", self.update_value)
            self.connect(self.bliss_obj, "state", self.update_state)
            self.__saved_state = self.get_value()
        elif self.device_type == "motor":
            self.connect(self.bliss_obj, "position", self.update_value)
            self.connect(self.bliss_obj, "state", self._update_state_motor)

    def get_value(self):
        """Get the device value
        Returns:
            (str): The value or "unknown"
        """
        if self.device_type == "motor":
            _val = self._bliss_obj.position
        elif self.device_type == "actuator":
            _val = self._bliss_obj.state

        try:
            _key = [key for key, val in self.predefined_values.items() if val == _val][
                0
            ]
        except IndexError:
            _key = "unknown"
        return _key

    def _set_value(self, value):
        """Set device to value.
        Args:
            value (str): target value
        """
        if self.device_type == "motor":
            self._bliss_obj.move(self.predefined_values[value], wait=False)
        elif self.device_type == "actuator":
            _attr = "set_" + self.predefined_values[value].lower()
            _cmd = getattr(self._bliss_obj, _attr)
            _cmd()
            self.__saved_state = value

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        try:
            _state = self._bliss_obj.state.upper()
        except (AttributeError, KeyError):
            return self.STATES.UNKNOWN

        if _state in ("IN", "OUT"):
            if self.__saved_state == _state:
                _state = self.STATES.READY
            else:
                _state = self.STATES.BUSY
        else:
            try:
                self.SPECIFIC_STATES.__members__[_state].value[0]
            except KeyError:
                _state = self.STATES.__members__[_state]
        return _state

    def _update_state_motor(self, state):
        try:
            state = self.SPECIFIC_STATES.__members__[state.upper()].value[0]
        except (AttributeError, KeyError):
            state = self.STATES.UNKNOWN
        return self.update_state(state)

    def _wait_ready(self, timeout=None):
        """Wait for the state to be ready.
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

    def _ready(self):
        """Check if the device is ready"""
        _state = self.get_state()
        return _state == self.STATES.READY

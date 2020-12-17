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
bliss implementation of AbstartNState
Example xml file:
<device class="BlissNState">
  <username>Detector Cover</username>
  <object_name>detcover</>
  <object href="/bliss" role="controller"/>
  <values>{"IN": "IN", "OUT": "OUT"}</values>
</device>
"""
from enum import Enum
from mx3core.HardwareObjects.abstract.AbstractMotor import MotorStates
from mx3core.HardwareObjects.abstract.AbstractNState import (
    AbstractNState,
    BaseValueEnum,
)

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
        _name = self.get_property("object_name")
        self._bliss_obj = getattr(self.get_object_by_role("controller"), _name)

        self.device_type = "actuator"
        if "MultiplePositions" in self._bliss_obj.__class__.__name__:
            self.device_type = "motor"

        self.initialise_values()
        if self.device_type == "actuator":
            self.connect(self._bliss_obj, "state", self.update_value)
            self.connect(self._bliss_obj, "state", self._update_state)
            self.__saved_state = self.get_value()
        elif self.device_type == "motor":
            self.connect(self._bliss_obj, "position", self.update_value)
            self.connect(self._bliss_obj, "state", self._update_state_motor)

        self.update_state()

    def _update_state(self, state):
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        if self.device_type == "motor":
            _val = self._bliss_obj.position
        elif self.device_type == "actuator":
            _val = self._bliss_obj.state

        return self.value_to_enum(_val)

    def _set_value(self, value):
        """Set device to value.
        Args:
            value (str or enum): target value
        """
        self.update_state(self.STATES.BUSY)

        if isinstance(value, Enum):
            self.__saved_state = value.name
            if isinstance(value.value, tuple) or isinstance(value.value, list):
                value = value.value[0]
            else:
                value = value.value
        else:
            self.__saved_state = value.upper()
        if self.device_type == "motor":
            self._bliss_obj.move(value, wait=False)
        elif self.device_type == "actuator":
            _attr = "set_" + value.lower()
            _cmd = getattr(self._bliss_obj, _attr)
            _cmd()

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

    def initialise_values(self):
        """Get the predefined valies. Create the VALUES Enum
        Returns:
            (Enum): "ValueEnum" with predefined values.
        """
        if self.device_type == "actuator":
            super(BlissNState, self).initialise_values()
        if self.device_type == "motor":
            values = {val.upper(): val for val in self.bliss_obj.positions_list}
            self.VALUES = Enum(
                "ValueEnum",
                dict(values, **{item.name: item.value for item in BaseValueEnum}),
            )

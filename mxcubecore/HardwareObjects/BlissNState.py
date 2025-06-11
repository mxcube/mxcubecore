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

Example yaml file:

.. code-block:: yaml

 class: BlissNState.BlissNState
 configuration:
    actuator_name: detcover
    prefix: detcov   # optional
    type: actuator   # actuaror or motor, default value actuator
    username: Detector Cover
    values: {"IN": "IN", "OUT": "OUT"}  # optional
  objects:
    controller: bliss.yml
"""

from enum import Enum

from mxcubecore.HardwareObjects.abstract.AbstractNState import (
    AbstractNState,
    BaseValueEnum,
)
from mxcubecore.HardwareObjects.BlissMotor import BlissMotor

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissNState(AbstractNState):
    """bliss implementation of AbstartNState"""

    def __init__(self, name):
        super().__init__(name)
        self._bliss_obj = None
        self.device_type = None
        self.__saved_state = None
        self._prefix = None

    def init(self):
        """Initialise the device"""

        super().init()
        self._prefix = self.get_property("prefix")
        self._bliss_obj = getattr(
            self.get_object_by_role("controller"), self.actuator_name
        )

        self.device_type = self.get_property("type", "actuator")
        if "MultiplePositions" in self._bliss_obj.__class__.__name__:
            self.device_type = "motor"

        self.initialise_values()
        self.__saved_state = self.get_value().value
        if self.device_type == "actuator":
            self.connect(self._bliss_obj, "state", self._update_value)
            self.connect(self._bliss_obj, "state", self._update_state)
        elif self.device_type == "motor":
            self.connect(self._bliss_obj, "position", self._update_value)
            self.connect(self._bliss_obj, "state", self._update_state_motor)

        self.update_value()
        self.update_state()

    # NB: Bliss calls the update handler with the state so its needed in the
    # method definition
    def _update_state(self, state=None):
        self.update_state(self.STATES.READY)

    def _update_value(self, value=None):
        if value:
            self.update_value(self.value_to_enum(value))
        else:
            self.update_value()

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        if self.device_type == "motor":
            return self.value_to_enum(self._bliss_obj.position)

        if self.device_type == "actuator":
            if self._prefix:
                _attr = self._prefix + "_is_in"
                _cmd = getattr(self._bliss_obj, _attr)
                if isinstance(_cmd, bool):
                    _val = _cmd
                else:
                    _val = _cmd()
            else:
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
            if isinstance(value.value, (tuple, list)):
                svalue = value.value[0]
            else:
                svalue = value.value
        else:
            self.__saved_state = value.upper()
        # are we sure we never get to need svalue below without setting it first?
        if self.device_type == "motor":
            self._bliss_obj.move(svalue, wait=False)
        elif self.device_type == "actuator":
            if self._prefix:
                _attr = self._prefix + "_" + value.name.lower()
            else:
                _attr = "set_" + svalue.lower()
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

        if self.device_type == "motor":
            try:
                return BlissMotor.SPECIFIC_TO_HWR_STATE[_state]
            except KeyError:
                return self.STATES.UNKNOWN

        if _state in ("IN", "OUT"):
            if self.__saved_state == _state:
                return self.STATES.READY
            return self.STATES.BUSY
        return self.STATES.UNKNOWN

    def _update_state_motor(self, state):
        """Update the state for the motor type."""
        try:
            state = BlissMotor.SPECIFIC_TO_HWR_STATE[state.upper()]
        except KeyError:
            state = self.STATES.UNKNOWN
        return self.update_state(state)

    def initialise_values(self):
        """Get the predefined valies. Create the VALUES Enum
        Returns:
            (Enum): "ValueEnum" with predefined values.
        """
        if self.device_type == "actuator":
            super().initialise_values()
        if self.device_type == "motor":
            try:
                values = {
                    val["label"].upper(): val["label"]
                    for val in self._bliss_obj.positions_list
                }
                self.VALUES = Enum(
                    "ValueEnum",
                    dict(values, **{item.name: item.value for item in BaseValueEnum}),
                )
            except AttributeError:
                super().initialise_values()

# encoding: utf-8
#
#  Project name: MXCuBE
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
    type: actuator   # actuaror or motor, default value actuator
    username: Detector Cover
    values: {"IN": "IN", "OUT": "OUT"}  # optional
"""

from enum import Enum
import logging
from gevent import Timeout

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractNState import (
    AbstractNState,
    BaseValueEnum,
)
from mxcubecore.HardwareObjects.BlissMotor import BlissMotor

_log = logging.getLogger("MX3.HWR")

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissNState(AbstractNState):
    """bliss implementation of AbstartNState"""

    def __init__(self, name):
        super().__init__(name)
        self._bliss_obj = None
        self.device_type = None
        self.__saved_state = None
        self._motor_callback = None

    def init(self):
        """Initialise the device"""

        super().init()
        self._bliss_obj = None
        try:
            bliss_proxy = HWR.beamline.bliss_proxy
            bliss_proxy.hardware.register(self.actuator_name)
            self._bliss_obj = bliss_proxy.get_object(self.actuator_name)
        except Exception as exc:
            msg = f"BlissNState: {self.actuator_name} not available {exc}"
            _log.warning(msg)

        self.device_type = self.get_property("type", "actuator")
        try:
            if "multiposition" in self._bliss_obj.type:
                self.device_type = "motor"
        except AttributeError:
            pass

        self.initialise_values()

        self.__saved_state = self.get_value().value

        if self._bliss_obj is not None:
            self._bliss_obj.subscribe("property", self._on_property_changed)
            self._bliss_obj.subscribe("online", self._on_online_changed)

        self.update_value()
        self.update_state()

    def _on_online_changed(self, online: bool) -> None:
        """Callback for online/offline events received via blissclient."""
        if not online:
            self.update_state(HardwareObjectState.UNKNOWN)
        else:
            self.update_value()
            self.update_state()

    def _on_property_changed(self, data: dict) -> None:
        """Callback for property changes received via blissclient."""
        if "position" in data or "state" in data:
            self.update_value(self.get_value())
            self.update_state(self.get_state())

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        if self._bliss_obj is None or self.device_type is None:
            return self.VALUES.UNKNOWN
        if self.device_type == "motor":
            return self.value_to_enum(self._bliss_obj.position)
        if self.device_type == "actuator":
            state_val = self._bliss_obj.state
            if isinstance(state_val, list):
                _val = state_val[0] if state_val else "UNKNOWN"
            else:
                _val = state_val or "UNKNOWN"

            return self.value_to_enum(_val)
        return self.VALUES.UNKNOWN

    def _set_value(self, value):
        """Set device to value.
        Args:
            value (str or enum): target value
        """
        if self._bliss_obj is None:
            raise RuntimeError(
                f"BlissNState '{self.actuator_name}' is offline — BLISS object not available"
            )
        self.update_state(self.STATES.BUSY)
        if isinstance(value, Enum):
            self.__saved_state = value.name
            if isinstance(value.value, (tuple, list)):
                svalue = value.value[0]
            else:
                svalue = value.value
        else:
            self.__saved_state = value.upper()

        if self.device_type == "motor":
            # with blissclient this is a non blocking move
            self._motor_callback = self._bliss_obj.move(svalue)
        elif self.device_type == "actuator":
            if value.name == "IN": #tried value but only name working
                self._motor_callback = self._bliss_obj.move_in()
            if value.name == "OUT":
                self._motor_callback = self._bliss_obj.move_out()

    def _get_state_str(self) -> str:
        """Return the current state as an uppercase string.
        Handles both list (actuator/motor axis) and plain string (multiposition).
        """
        try:
            state_val = self._bliss_obj.state
            if state_val is None:
                # multiposition may not expose state at top level; use properties
                state_val = self._bliss_obj.properties.get("state")
            if isinstance(state_val, list):
                return state_val[0].upper() if state_val else "UNKNOWN"
            return str(state_val).upper() if state_val else "UNKNOWN"
        except (AttributeError, IndexError):
            return "UNKNOWN"

    def get_state(self):
        try:
            _state = self._bliss_obj.state
        except AttributeError:
            return self.STATES.UNKNOWN

        if _state == "ERROR":
            return self.STATES.FAULT

        if self.device_type == "motor":
            return BlissMotor.SPECIFIC_TO_HWR_STATE[_state]

        if self.device_type == "actuator":
            if _state in ("IN", "OUT"):
                if self.__saved_state == _state:
                    return self.STATES.READY
                return self.STATES.BUSY
        return self.STATES.UNKNOWN

    def wait_ready(self, timeout: float | None = None):
        if self._motor_callback is None:
            return
        with Timeout(timeout, RuntimeError("Timeout waiting for device to be ready")):
            self._motor_callback.get(monitor_interval=0.2)
        self.update_state()
        self.update_value()

    def initialise_values(self):
        """Get the predefined values. Create the VALUES Enum
        Returns:
            (Enum): "ValueEnum" with predefined values.
        """
        # Always load values from config first so VALUES is never empty
        # (this is also called from AbstractNState.init before device_type is set)
        super().initialise_values()
        if self.device_type == "motor":
            try:
                positions = self._bliss_obj.properties.get("positions", [])
                values = {
                    pos["position"].upper(): pos["position"]
                    for pos in positions
                    if "position" in pos
                }
                self.VALUES = Enum(
                    "ValueEnum",
                    dict(values, **{item.name: item.value for item in BaseValueEnum}),
                )
            except (AttributeError, KeyError, TypeError):
                super().initialise_values()

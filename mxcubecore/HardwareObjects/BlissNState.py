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
    prefix: detcov   # optional
    type: actuator   # actuaror or motor, default value actuator
    username: Detector Cover
    values: {"IN": "IN", "OUT": "OUT"}  # optional
"""

from enum import Enum
import logging

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

    def init(self):
        """Initialise the device"""

        super().init()
        self._bliss_obj = HWR.beamline.bliss_proxy.get_object(self.actuator_name)

        _log.info(
            "[BlissNState] %s: bliss_obj=%s, type_attr=%s, properties=%s",
            self.actuator_name,
            self._bliss_obj,
            getattr(self._bliss_obj, "type", "<no type attr>"),
            getattr(self._bliss_obj, "properties", "<no properties attr>"),
        )

        self.device_type = self.get_property("type", "actuator")
        try:
            if "multiposition" in self._bliss_obj.type.lower():
                self.device_type = "motor"
        except Exception as exc:
            _log.warning("[BlissNState] %s: could not read .type: %s", self.actuator_name, exc)

        self.initialise_values()
        non_unknown = [v for v in self.VALUES if v.name != "UNKNOWN"]
        if self.device_type == "actuator" and len(non_unknown) > 2:
            _log.info(
                "[BlissNState] %s: promoting to motor (>2 positions: %s)",
                self.actuator_name, [v.name for v in non_unknown],
            )
            self.device_type = "motor"

        _log.info(
            "[BlissNState] %s: device_type=%s, VALUES=%s",
            self.actuator_name, self.device_type, [v.name for v in self.VALUES],
        )

        raw_state = getattr(self._bliss_obj, "state", "<no state>")
        raw_pos = getattr(self._bliss_obj, "position", "<no position>")
        _log.info(
            "[BlissNState] %s: .state=%s, .position=%s",
            self.actuator_name, raw_state, raw_pos,
        )

        self.__saved_state = self.get_value().name
        _log.info(
            "[BlissNState] %s: initial get_value()=%s",
            self.actuator_name, self.__saved_state,
        )

        self._bliss_obj.subscribe("property", self._on_property_changed)
        self._bliss_obj.subscribe("online", self._on_online_changed)

        self.update_value(self.get_value())
        self.update_state(self.get_state())

    def _on_online_changed(self, online: bool) -> None:
        """Callback for online/offline events received via blissclient."""
        if not online:
            self.update_state(HardwareObjectState.UNKNOWN)
        else:
            self.update_value(self.get_value())
            self.update_state(self.get_state())

    def _on_property_changed(self, data: dict) -> None:
        """Callback for property changes received via blissclient."""
        if self.device_type == "motor":
            if "position" in data:
                self.update_value(self.value_to_enum(data["position"]))
            if "state" in data:
                state_val = data["state"]
                if isinstance(state_val, list):
                    _state = state_val[0].upper() if state_val else "UNKNOWN"
                else:
                    _state = str(state_val).upper() if state_val else "UNKNOWN"
                if _state == "ERROR":
                    _hwr_state = HardwareObjectState.FAULT
                else:
                    _hwr_state = BlissMotor.SPECIFIC_TO_HWR_STATE.get(
                        _state, HardwareObjectState.UNKNOWN
                    )
                self.update_state(_hwr_state)
        elif self.device_type == "actuator":
            if "state" in data or "position" in data:
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
            position = self._bliss_obj.position
            if position is None:
                # multiposition exposes named position in properties, not top-level
                position = self._bliss_obj.properties.get("position")
            result = self.value_to_enum(position)
            _log.debug(
                "[BlissNState] %s get_value motor: .position=%s -> %s",
                self.actuator_name, position, result.name,
            )
            return result

        if self.device_type == "actuator":
            state_val = self._bliss_obj.state
            if isinstance(state_val, list):
                _val = state_val[0] if state_val else "UNKNOWN"
            else:
                _val = state_val if state_val else "UNKNOWN"

            _val_upper = str(_val).upper()

            # 1. Direct value match (e.g. Bliss reports "BEAM", VALUES has IN: "BEAM")
            result = self.value_to_enum(_val)
            if result != self.VALUES.UNKNOWN:
                return result

            if _val_upper != "UNKNOWN":
                # 2. Name match (Bliss actuator reports "IN"/"OUT" as state string)
                try:
                    return self.VALUES[_val_upper]
                except KeyError:
                    pass

                # 3. Transition state (MOVING, READY…): fall back to last commanded
                #    position so the UI shows something meaningful during moves.
                if self.__saved_state and self.__saved_state.upper() != "UNKNOWN":
                    try:
                        return self.VALUES[self.__saved_state.upper()]
                    except KeyError:
                        pass

            return self.VALUES.UNKNOWN

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
            svalue = value.upper()

        if self.device_type == "motor":
            self._bliss_obj.move(svalue)
        elif self.device_type == "actuator":
            # Use enum NAME (IN / OUT) to decide the move call so that physical
            # value strings like "BEAM" / "OFF" are handled correctly.
            enum_name = value.name if isinstance(value, Enum) else svalue.upper()
            if enum_name == "IN":
                self._bliss_obj.move_in()
            elif enum_name == "OUT":
                self._bliss_obj.move_out()
            elif hasattr(self._bliss_obj, "move"):
                # Named positions (PARK, TRANSFER, …) on actuators that
                # expose a generic move() method.
                self._bliss_obj.move(svalue)
            else:
                raise ValueError(
                    f"Actuator {self.actuator_name}: unsupported target value '{svalue}'. "
                    "Expected 'IN' or 'OUT'."
                )

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
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        _state = self._get_state_str()
        if _state == "UNKNOWN":
            return self.STATES.UNKNOWN

        if self.device_type == "motor":
            if _state == "ERROR":
                return self.STATES.FAULT
            return BlissMotor.SPECIFIC_TO_HWR_STATE.get(_state, self.STATES.UNKNOWN)

        # actuator
        if _state == "ERROR":
            return self.STATES.FAULT

        # Standard Bliss motor/actuator states (READY, MOVING, OFF, …)
        hwr_state = BlissMotor.SPECIFIC_TO_HWR_STATE.get(_state)
        if hwr_state is not None:
            return hwr_state

        # If the state string matches a known physical value the device is
        # stably at a position → READY (handles e.g. "BEAM", "OFF", "PARK")
        for enum_var in self.VALUES:
            val = enum_var.value
            if isinstance(val, (tuple, list)):
                if _state in [str(v).upper() for v in val]:
                    return self.STATES.READY
            elif isinstance(val, str) and val.upper() == _state:
                return self.STATES.READY

        # Legacy: actuators that report "IN" / "OUT" directly as state
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
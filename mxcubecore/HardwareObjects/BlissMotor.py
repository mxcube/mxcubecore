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
Example yml configuration:

.. code-block:: yaml

 class: BlissMotor.BlissMotor
 configuration:
   actuator_name: dtox
   username: Detector Distance
"""

import enum
import threading
import time

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.BlissProxy import BlissProxy
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@enum.unique
class BlissMotorStates(enum.Enum):
    """
    MOVING = "Axis is moving"
    READY = "Axis is ready to be moved (not moving ?)"
    FAULT = "Error from controller"
    LIMPOS = "Hardware high limit active"
    LIMNEG = "Hardware low limit active"
    HOME = "Home signal active"
    OFF = "Axis power is off"
    DISABLED = "Axis cannot move"
    """

    MOVING = 0
    READY = 1
    FAULT = 2
    LIMPOS = 3
    LIMNEG = 4
    HOME = 5
    OFF = 6
    DISABLED = 7
    UNKNOWN = 8


class BlissMotor(AbstractMotor, BlissProxy):
    """Bliss Motor implementation"""

    SPECIFIC_STATES = BlissMotorStates
    SPECIFIC_TO_HWR_STATE = {
        "MOVING": HardwareObjectState.BUSY,
        "READY": HardwareObjectState.READY,
        "FAULT": HardwareObjectState.FAULT,
        "LIMPOS": HardwareObjectState.READY,
        "LIMNEG": HardwareObjectState.READY,
        "HIGHLIMIT": HardwareObjectState.READY,
        "LOWLIMIT": HardwareObjectState.READY,
        "HOME": HardwareObjectState.READY,
        "OFF": HardwareObjectState.OFF,
        "DISABLED": HardwareObjectState.OFF,
        "UNKNOWN": HardwareObjectState.UNKNOWN,
    }

    def __init__(self, name):
        super().__init__(name)
        self.motor_obj = None

    def init(self):
        """Initialise the motor"""
        super().init()
        BlissProxy.init(self)
        self.motor_obj = self.get_object(self.actuator_name)

        # init state to match motor's one
        self.update_state(self.get_state())
        self.update_limits(self.get_limits())
        self.update_value(self.get_value())

        self.motor_obj.subscribe("property", self._on_property_changed)
        self.motor_obj.subscribe("online", self._on_online_changed)

    def _on_online_changed(self, online: bool) -> None:
        """Callback for motor online/offline events received via blissclient."""
        if not online:
            self.update_state(HardwareObjectState.UNKNOWN)
        else:
            self._update_state()

    def _on_property_changed(self, data: dict) -> None:
        """Callback for property changes received via blissclient."""
        if "position" in data:
            self.update_value(data["position"])
        if "state" in data:
            self._update_state()

    def _state2enum(self, state):
        """Translate the state to HardwareObjectState and BlissMotorStates
        Args:
           state (string): state
        Returns:
           (tuple): (HardwareObjectState, BlissMotorStates)
        """
        try:
            _specific_state = BlissMotorStates[state]
        except (TypeError, KeyError):
            _specific_state = BlissMotorStates.UNKNOWN

        _state = self.SPECIFIC_TO_HWR_STATE.get(state, HardwareObjectState.UNKNOWN)
        return _state, _specific_state

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum HardwareObjectState): Motor state.
        """
        # Via BlissProxy the REST API returns state as a list of strings.
        state = HardwareObjectState.UNKNOWN
        for stat in self.motor_obj.state or []:
            try:
                return HardwareObjectState[stat]
            except KeyError:
                if stat in ("DISABLED", "OFF"):
                    return HardwareObjectState.OFF
                if stat == "MOVING":
                    return HardwareObjectState.BUSY
                state = self._state2enum(stat)[0]
        return state

    def get_specific_state(self):
        """Get the motor state.
        Returns:
            (list): Motor states as list of BlissMotorStates enum
        """
        state_list = []
        for _state in self.motor_obj.state or []:
            state_list.append(self._state2enum(_state)[1])
        return state_list

    def _update_state(self):
        """Refresh state from the motor object and emit stateChanged if it changed."""
        _state = self.get_state()
        self._specific_state = self.get_specific_state()
        self.update_state(_state)

    def get_value(self):
        """Read the motor position.
        Returns:
            float: Motor position.
        """
        pos = self.motor_obj.position
        if pos is None:
            # motor_obj.position can be None during init or if REST call returns null
            return self._nominal_value if self._nominal_value is not None else 0.0
        return pos

    def get_limits(self):
        """Returns motor low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        # no limit = None, but None is a problematic value for some
        # GUI components (like MotorSpinBox), so instead we return
        # very large value. The same is if limits contain -inf or +inf.

        _low, _high = self.motor_obj.limits
        _low = _low or -1e6
        _high = _high or 1e6
        if _low in (float("-inf"), float("+inf")):
            _low = -1e6 if _low < 0 else 1e6
        if _high in (float("-inf"), float("+inf")):
            _high = -1e6 if _high < 0 else 1e6

        self._nominal_limits = (_low, _high)
        return self._nominal_limits

    def get_velocity(self):
        """Read motor velocity.
        Returns:
            (float): velocity [unit/s]
        """
        self._velocity = self.motor_obj.velocity
        return self._velocity

    def _set_value(self, value):
        """Move motor to absolute value.
        Args:
            value (float): target value
        Note: move() is non-blocking — it fires the REST request and returns a
              future.  The state is optimistically set to BUSY immediately so
              that wait_ready() (called by set_value when timeout > 0) does not
              return before the first MOVING event arrives via socket.io.
        """
        self.update_state(HardwareObjectState.BUSY)
        self.motor_obj.move(value)

        def _poll_completion():
            deadline = time.time() + 300  # 5-minute safety timeout
            while time.time() < deadline:
                time.sleep(0.5)
                try:
                    states = self.motor_obj.state or []
                    if "MOVING" not in states:
                        self._update_state()
                        self.update_value(self.get_value())
                        return
                except Exception:
                    pass
            self._update_state()

        threading.Thread(
            target=_poll_completion, daemon=True, name="bliss-motor-poll"
        ).start()

    def abort(self):
        """Stop the motor movement"""
        try:
            self.motor_obj.stop()
        except Exception:
            pass
        self._update_state()
        self.update_value(self.get_value())

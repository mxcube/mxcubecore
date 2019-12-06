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
Example xml file:
<device class="ExporterMotor">
  <username>phiy</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <motor_name>AlignmentY</motor_name>
  <tolerance>1e-2</tolerance>
</device>
"""

import sys

from gevent import Timeout, sleep
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)
from HardwareRepository.Command.Exporter import Exporter

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ExporterMotor(AbstractMotor):
    """API for motor using the Exporter protocol, based on AbstractMotor"""

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.username = None
        self._motor_pos_suffix = "Position"
        self._motor_state_suffix = "State"
        self._exporter = None
        self.__position = None
        self.__motor_state = None

    def init(self):
        """Initialise the motor"""
        AbstractMotor.init(self)
        _exporter_address = self.getProperty("exporter_address")
        _host, _port = _exporter_address.split(":")
        self._exporter = Exporter(_host, int(_port))

        self.__position = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "position",
            },
            self.motor_name + self._motor_pos_suffix,
        )

        if self.__position:
            self.__position.connectSignal("update", self.update_position)
            self.get_position()

        self.__motor_state = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "motor_state",
            },
            self.motor_name + self._motor_state_suffix,
        )

        if self.__motor_state:
            self.__motor_state.connectSignal("update", self.update_state)

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum 'MotorStates'): Motor state.
        """
        try:
            _state = self.__motor_state.get_value().upper()
            self.state = MotorStates.__members__[_state]
        except KeyError:
            self.state = MotorStates.UNKNOWN
        return self.state

    def _get_hwstate(self):
        """Get the hardware state, reported by the MD2 application.
        Returns:
            (string): The state.
        """
        try:
            return self._exporter.read_property("HardwareState")
        except BaseException:
            return "Ready"

    def _get_swstate(self):
        """Get the software state, reported by the MD2 application.
        Returns:
            (string): The state.
        """
        return self._exporter.read_property("State")

    def _ready(self):
        """Get the "Ready" state - software and hardware.
        Returns:
            (bool): True if both "Ready", False otherwise.
        """
        if self._get_swstate() == "Ready" and self._get_hwstate() == "Ready":
            return True
        return False

    def _wait_ready(self, timeout=3):
        """Wait for the state to be "Ready".
        Args:
            timeout (float): waiting time [s].
        Raises:
            RuntimeError: Execution timeout.
        """
        with Timeout(timeout, RuntimeError("Execution timeout")):
            while not self._ready():
                sleep(0.01)

    def wait_move(self, timeout=20):
        """Wait until the end of move ended, using the application state.
        Args:
            timeout(float): Timeout [s]. Default value is 20 s
        """
        self._wait_ready(timeout)

    def wait_motor_move(self, timeout=20):
        """Wait until the end of move ended using the motor state.
        Args:
            timeout(float): Timeout [s]. Default value is 20 s
        Raises:
            RuntimeError: Execution timeout.
        """
        with Timeout(timeout, RuntimeError("Execution timeout")):
            while self.get_state() != MotorStates.READY:
                sleep(0.01)

    def get_position(self):
        """Get the motor position.
        Returns:
            (float): Motor position.
        """
        self.position = self.__position.get_value()
        return self.position

    def get_limits(self):
        """Returns motor low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        try:
            _low, _high = self._exporter.execute("getMotorLimits", self.motor_name)
            # inf is a problematic value, convert to sys.float_info.max
            if _low == float("-inf"):
                _low = -sys.float_info.max

            if _high == float("inf"):
                _high = sys.float_info.max

            self._limits = (_low, _high)
        except ValueError:
            self._limits = (-1e4, 1e4)
        return self._limits

    def get_dynamic_limits(self):
        """Returns motor low and high dynamic limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        try:
            _low, _high = self._exporter.execute(
                "getMotorDynamicLimits", self.motor_name
            )
            # inf is a problematic value, convert to sys.float_info.max
            if _low == float("-inf"):
                _low = -sys.float_info.max

            if _high == float("inf"):
                _high = sys.float_info.max
            return _low, _high
        except ValueError:
            return -1e4, 1e4

    def _move(self, position, wait=True, timeout=None):
        """Move motor to absolute position. Wait the move to finish.
        Args:
            position (float): target position
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        self.__position.set_value(position)
        self.emit("stateChanged", (MotorStates.MOVING))

        if wait:
            self.wait_move(timeout)

    def stop(self):
        """Stop the motor movement immediately."""
        if self.get_state() != MotorStates.UNKNOWN:
            self._exporter.execute("abort")

    def abort(self):
        """Abort the motor movement immediately."""
        self.stop()

    def home(self, timeout=None):
        """Homing procedure.
        Args:
            timeout (float): optional - timeout [s].
        """
        self._exporter.execute("startHomingMotor", self.motor_name)

    def get_max_speed(self):
        """Get the motor maximum speed.
        Returns:
            (float): the maximim speed [unit/s].
        """
        return self._exporter.execute("getMotorMaxSpeed", self.motor_name)

    def update_values(self):
        """Emit signals to update the state, position and limits values."""
        self.emit("stateChanged", (self.get_state(),))
        self.emit("positionChanged", (self.get_position(),))
        if all(self._limits):
            self.emit("limitsChanged", (self.get_limits(),))

    def name(self):
        """Get the motor name. Should be removed when GUI ready"""
        return self.motor_name

#! /usr/bin/env python
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Example of using StandardHardwareObject: ExporterMotorExample (from ExporterMotor)
"""

from HardwareRepository.HardwareObjects.abstract import AbstractActuator

"""
Example xml file:
<device class="MicrodiffMotor">
  <username>phiy</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <motor_name>AlignmentY</motor_name>
  <GUIstep>1.0</GUIstep>
  <unit>-1e-3</unit>
  <resolution>1e-2</resolution>
</device>
"""


class ExporterMotorExample(AbstractActuator.AbstractActuator):
    def __init__(self, name):
        super(ExporterMotorExample, self).__init__(name)

        self.motor_name = None
        self.motor_pos_attr_suffix = None
        self.state_mapping = {}

    def init(self):
        self.motor_name = self.getProperty("motor_name")
        self.value_resolution = self.getProperty("resolution")
        if self.value_resolution is None:
            self.value_resolution = 0.0001
        self.motor_pos_attr_suffix = "Position"

        self.chan_position = self.add_channel(
            {"type": "exporter", "name": "%sPosition" % self.motor_name},
            self.motor_name + self.motor_pos_attr_suffix,
        )
        self.chan_position.connectSignal("update", self.value_changed)

        self.chan_state = self.add_channel(
            {"type": "exporter", "name": "state"}, "State"
        )
        self.chan_all_motor_states = self.add_channel(
            {"type": "exporter", "name": "motor_states"}, "MotorStates"
        )
        self.chan_all_motor_states.connectSignal(
            "update", self.all_motor_states_changed
        )

        self.cmd_abort = self.add_command({"type": "exporter", "name": "abort"}, "abort")
        self.cmd_get_dynamic_limits = self.add_command(
            {"type": "exporter", "name": "get%sDynamicLimits" % self.motor_name},
            "getMotorDynamicLimits",
        )
        self.cmd_get_limits = self.add_command(
            {"type": "exporter", "name": "get_limits"}, "getMotorLimits"
        )
        self.cmd_get_max_speed = self.add_command(
            {"type": "exporter", "name": "get_max_speed"}, "getMotorMaxSpeed"
        )
        self.cmd_home = self.add_command(
            {"type": "exporter", "name": "homing"}, "startHomingMotor"
        )

        # Map of state strings returned from channel to self.STATE
        # NB this is only an short example
        STATE = self.STATE
        self.state_mapping = {
            "Initializing": STATE.INITIALIZING,
            "Ready": STATE.READY,
            "Busy": STATE.BUSY,
            "Unknown": STATE.UNKNOWN,
            "NotInitialized": STATE.NOTINITIALIZED,
        }

        # Initialise values from channel
        self.set_state(self.STATE.READY)

    def connectNotify(self, signal):
        if signal == "valueChanged":
            self.emit("valueChanged", (self.get_value(),))
        elif signal == "stateChanged":
            self.emit("stateChanged", (self.get_state(),))
        elif signal == "limitsChanged":
            self.emit("limitsChanged", (self.get_limits(),))

    def all_motor_states_changed(self, all_motor_states):
        """Get state for all known motors"""

        dd0 = dict([x.split("=") for x in all_motor_states])
        # Some are like motors but have no state
        # we set them to ready
        if dd0.get(self.motor_name) is None:
            new_state = self.STATE.READY
        else:
            new_state = self.state_mapping.get(dd0[self.motor_name], self.STATE.UNKNOWN)

        self.state = new_state

    def get_limits(self):
        """ Get current limits, dynamic or static

        Returns:
            Tuple[float,float]

        """
        dynamic_limits = self.get_dynamic_limits()
        if dynamic_limits == (-1e4, 1e4):
            try:
                low_lim, hi_lim = map(float, self.cmd_get_limits(self.motor_name))
                if low_lim == float(1e999) or hi_lim == float(1e999):
                    raise ValueError
                return low_lim, hi_lim
            except BaseException:
                return (-1e4, 1e4)
        else:
            return dynamic_limits

    def get_max_speed(self):
        """Maximum change speed in relevant units / s

        Returns:
            Optional[float]
        """
        return self.cmd_get_max_speed(self.motor_name)

    def get_value(self):
        """Get current value

        Returns:
            Optional[float]
        """
        return self.chan_position.getValue()

    def _set_value(self, value):
        self.set_state(self.STATE.BUSY)
        self.chan_position.setValue(value)

    def get_dynamic_limits(self):
        try:
            low_lim, hi_lim = map(float, self.cmd_get_dynamic_limits(self.motor_name))
            if low_lim == float(1e999) or hi_lim == float(1e999):
                raise ValueError
            return low_lim, hi_lim
        except BaseException:
            return (-1e4, 1e4)

    def stop(self):
        if self.get_state() != self.STATE.NOTINITIALIZED:
            self.cmd_abort()

    def home(self, timeout=None):
        if not isinstance(timeout, (int, float)) or timeout < 0:
            raise ValueError("Invalid value for timeout: %s" % timeout)
        self.cmd_home(self.motor_name)
        self.wait_ready(timeout)

    def value_changed(self, value, private={}):
        self.emit("valueChanged", (value,))

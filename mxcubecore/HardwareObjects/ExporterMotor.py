import math
import logging
import time
from gevent import Timeout
from AbstractMotor import AbstractMotor

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


class ExporterMotor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.motor_name = None
        self.motor_resolution = None
        self.motor_pos_attr_suffix = None

    def init(self):
        self.motor_name = self.getProperty("motor_name")
        self.motor_resolution = self.getProperty("resolution")
        if self.motor_resolution is None:
            self.motor_resolution = 0.0001
        self.motor_pos_attr_suffix = "Position"

        self.chan_position = self.addChannel(
            {"type": "exporter", "name": "%sPosition" % self.motor_name},
            self.motor_name + self.motor_pos_attr_suffix,
        )
        self.chan_position.connectSignal("update", self.position_changed)

        self.chan_state = self.addChannel(
            {"type": "exporter", "name": "state"}, "State"
        )
        self.chan_all_motor_states = self.addChannel(
            {"type": "exporter", "name": "motor_states"}, "MotorStates"
        )
        self.chan_all_motor_states.connectSignal(
            "update", self.all_motor_states_changed
        )

        self.cmd_abort = self.addCommand({"type": "exporter", "name": "abort"}, "abort")
        self.cmd_get_dynamic_limits = self.addCommand(
            {"type": "exporter", "name": "get%sDynamicLimits" % self.motor_name},
            "getMotorDynamicLimits",
        )
        self.cmd_get_limits = self.addCommand(
            {"type": "exporter", "name": "get_limits"}, "getMotorLimits"
        )
        self.cmd_get_max_speed = self.addCommand(
            {"type": "exporter", "name": "get_max_speed"}, "getMotorMaxSpeed"
        )
        self.cmd_home = self.addCommand(
            {"type": "exporter", "name": "homing"}, "startHomingMotor"
        )

        self.position_changed(self.chan_position.getValue())
        self.set_state(self.motor_states.READY)

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.emit("positionChanged", (self.get_position(),))
        elif signal == "stateChanged":
            self.emit("stateChanged", (self.get_state(),))
        elif signal == "limitsChanged":
            self.emit("limitsChanged", (self.get_limits(),))

    def all_motor_states_changed(self, all_motor_states):
        d = dict([x.split("=") for x in all_motor_states])
        # Some are like motors but have no state
        # we set them to ready
        if d.get(self.motor_name) is None:
            new_motor_state = self.motor_states.READY
        else:
            new_motor_state = self.motor_states.fromstring(d[self.motor_name])

        if self.get_state() != new_motor_state:
            self.set_state(new_motor_state)

    def limits_changed(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def get_limits(self):
        dynamic_limits = self.get_dynamic_limits()
        if dynamic_limits != (-1E4, 1E4):
            return dynamic_limits
        else:
            try:
                low_lim, hi_lim = map(float, self.cmd_get_limits(self.motor_name))
                if low_lim == float(1E999) or hi_lim == float(1E999):
                    raise ValueError
                return low_lim, hi_lim
            except BaseException:
                return (-1E4, 1E4)

    def get_dynamic_limits(self):
        try:
            low_lim, hi_lim = map(float, self.cmd_get_dynamic_limits(self.motor_name))
            if low_lim == float(1E999) or hi_lim == float(1E999):
                raise ValueError
            return low_lim, hi_lim
        except BaseException:
            return (-1E4, 1E4)

    def get_max_speed(self):
        return self.cmd_get_max_speed(self.motor_name)

    def position_changed(self, position, private={}):
        if None not in (position, self.get_position()):
            if abs(position - self.get_position()) <= self.motor_resolution:
                return
        self.set_position(position)
        self.emit("positionChanged", (position,))

    def move(self, position, wait=False, timeout=None):
        # if self.getState() != MicrodiffMotor.NOTINITIALIZED:
        if abs(self.get_position() - position) >= self.motor_resolution:
            self.chan_position.setValue(position)  # absolutePosition-self.offset)
        if timeout:
            self.wait_end_of_move(timeout)

    def wait_end_of_move(self, timeout=None):
        with Timeout(timeout):
            time.sleep(0.1)
            while not self.is_ready():
                time.sleep(0.1)

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        if self.get_state() != self.motor_states.NOTINITIALIZED:
            self.cmd_abort()

    def home(self, timeout=None):
        self.cmd_home(self.motor_name)
        if timeout:
            self.wait_end_of_move(timeout)

"""
EPICS implementation of AbstractNState.
Example xml file:
<device class="LNLS.LNLSInOut">
  <channel type="epics" name="epicsActuator_val">SOL:S:m4.SET</channel>
  <channel type="epics" name="epicsActuator_rbv" polling="500">SOL:S:m4.SET</channel>
  <username>Microdiff backlight</username>
  <motor_name>BackLightIsOn</motor_name>
  <values>{"in": True, "out": False}</values>
</device>
"""
import logging

from enum import Enum
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState
from HardwareRepository.HardwareObjects.LNLS.EPICSActuator import EPICSActuator


class EPICSNState(AbstractNState, EPICSActuator):

    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self.username = "unknown"
        self.actuatorState = "unknown"
        self.state_attr = None

    def init(self):
        AbstractNState.initialise_values(self)
        self.username = self.getProperty("username")
        self.states = dict((item.value, item.name) for item in self.VALUES)
        self.moves = dict((item.name, item.value) for item in self.VALUES)
        self.get_actuator_state()

    def connectNotify(self, signal):
        if signal == "actuatorStateChanged":
            self.valueChanged(self.state_attr)

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        if isinstance(value, Enum):
            try:
                value = value.value[0]
            except TypeError:
                value = value.value
        EPICSActuator._set_value(self, value)
        #self.set_channel_value(self.ACTUATOR_VAL, value)
        self.update_state()

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        value = EPICSActuator.get_value(self)
        #value = self.get_channel_value(self.ACTUATOR_RBV)
        return self.value_to_enum(value)

    def get_actuator_state(self, read=False):
        current_value = self.get_value()
        self.state_attr = current_value.value # Bool
        self.actuatorState = self.states.get(self.state_attr, "unknown") # Name
        return self.actuatorState

    def valueChanged(self, value):
        enum_val = self.value_to_enum(value)
        self.set_value(enum_val)
        self.actuatorState = self.states.get(value, "unknown")
        self.emit("actuatorStateChanged", (self.actuatorState,))
    
    def actuatorIn(self, wait=True, timeout=None):
        try:
            self.state_attr = self.moves["in"]
            self.valueChanged(self.state_attr)
        except BaseException:
            logging.getLogger("user_level_log").error(
                "Cannot put %s in", self.username
            )

    def actuatorOut(self, wait=True, timeout=None):
        try:
            self.state_attr = self.moves["out"]
            self.valueChanged(self.state_attr)
        except BaseException as e:
            logging.getLogger("user_level_log").error(
                "Cannot put %s out: %s", (self.username, e)
            )
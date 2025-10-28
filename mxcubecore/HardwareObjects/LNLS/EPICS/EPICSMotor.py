import time

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator


class EPICSMotor(EPICSActuator, AbstractMotor):
    """EPICS Motor class"""

    MOTOR_DMOV = "dmov"
    MOTOR_STOP = "stop"
    MOTOR_VELO = "velo"
    MOTOR_HLM = "hlm"
    MOTOR_LLM = "llm"
    MOTOR_EGU = "egu"
    MOTOR_PREC = "prec"

    def _instantiate_attributes(self):
        pvname = self._CommandContainer__channels[""].command.pv_name
        self.add_channel({"type": "epics", "name": self.ACTUATOR_VAL}, pvname + ".VAL")
        self.add_channel({"type": "epics", "name": self.ACTUATOR_RBV}, pvname + ".RBV")
        self.add_channel({"type": "epics", "name": self.MOTOR_DMOV}, pvname + ".DMOV")
        self.add_channel({"type": "epics", "name": self.MOTOR_STOP}, pvname + ".STOP")
        self.add_channel({"type": "epics", "name": self.MOTOR_VELO}, pvname + ".VELO")
        self.add_channel({"type": "epics", "name": self.MOTOR_HLM}, pvname + ".HLM")
        self.add_channel({"type": "epics", "name": self.MOTOR_LLM}, pvname + ".LLM")
        self.add_channel({"type": "epics", "name": self.MOTOR_EGU}, pvname + ".EGU")
        self.add_channel({"type": "epics", "name": self.MOTOR_PREC}, pvname + ".PREC")

    def init(self):
        """Initialization method"""
        self._motor_channels = {}
        self._instantiate_attributes()
        self.get_limits()
        self.get_velocity()
        self.get_precision()
        super().init()

    def _wait_actuator(self, value):
        """Override EPICSActuator method."""
        while not self.done_movement() or self.hasnt_arrived(value):
            time.sleep(0.25)
        self.update_state(self.STATES.READY)

    def abort(self):
        """Override EPICSActuator method."""
        self.set_channel_value(self.MOTOR_STOP, 1)
        super().abort()

    def get_limits(self):
        """Override AbstractActuator method."""
        try:
            low_limit = float(self.get_channel_value(self.MOTOR_LLM))
            high_limit = float(self.get_channel_value(self.MOTOR_HLM))
            self._nominal_limits = (low_limit, high_limit)
        except ValueError:
            self._nominal_limits = (None, None)
        if self._nominal_limits in [(0, 0), (float("-inf"), float("inf"))]:
            # Treat infinite limits
            self._nominal_limits = (None, None)
        return self._nominal_limits

    def get_velocity(self):
        """Override AbstractMotor method."""
        self._velocity = self.get_channel_value(self.MOTOR_VELO)
        return self._velocity

    def get_precision(self):
        self._tolerance = self.get_channel_value(self.MOTOR_PREC)

    def set_velocity(self, value):
        """Override AbstractMotor method."""
        self.set_channel_value(self.MOTOR_VELO, value)
        self._velocity = value

    def done_movement(self):
        """Return whether motor finished movement or not."""
        dmov = self.get_channel_value(self.MOTOR_DMOV)
        return bool(dmov)

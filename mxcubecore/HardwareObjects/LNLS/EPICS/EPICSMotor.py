import time

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator


class EPICSMotor(EPICSActuator, AbstractMotor):
    MOTOR_DMOV = "dmov"
    MOTOR_STOP = "stop"
    MOTOR_VELO = "velo"
    MOTOR_HLM = "hlm"
    MOTOR_LLM = "llm"
    MOTOR_EGU = "egu"
    MOTOR_PREC = "prec"

    def _instantiate_attributes(self):
        pvname = self.get_channel_object("").command.pv_name
        self.add_channel({"type": "epics", "name": self.ACTUATOR_VAL}, pvname + ".VAL")
        self.add_channel(
            {"type": "epics", "polling": 200, "name": self.ACTUATOR_RBV},
            pvname + ".RBV",
        )
        self.add_channel({"type": "epics", "name": self.MOTOR_DMOV}, pvname + ".DMOV")
        self.add_channel({"type": "epics", "name": self.MOTOR_STOP}, pvname + ".STOP")
        self.add_channel({"type": "epics", "name": self.MOTOR_VELO}, pvname + ".VELO")
        self.add_channel({"type": "epics", "name": self.MOTOR_HLM}, pvname + ".HLM")
        self.add_channel({"type": "epics", "name": self.MOTOR_LLM}, pvname + ".LLM")
        self.add_channel({"type": "epics", "name": self.MOTOR_EGU}, pvname + ".EGU")
        self.add_channel({"type": "epics", "name": self.MOTOR_PREC}, pvname + ".PREC")

    def init(self):
        self._motor_channels = {}
        self._instantiate_attributes()
        self.get_limits()
        self.get_velocity()
        self.get_precision()
        super().init()

    def _wait_thread(self, setpoint, timeout):
        if not timeout:
            timeout = (
                abs(self.get_channel_value("rbv") - setpoint) / self.get_velocity()
            )
            # Timeout tolerance
            timeout += 2.5
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while (
                    not self.done_movement() or self.hasnt_arrived(setpoint)
                ) and not self._wait_task.is_set():
                    time.sleep(0.15)
        except TimeoutError:
            self.log(
                f"{self.get_channel_object('').command.pv_name} motion has timed out."
            )
        self.update_state(self.STATES.READY)

    def abort(self):
        self.set_channel_value(self.MOTOR_STOP, 1)
        super().abort()

    def get_limits(self):
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
        self._velocity = self.get_channel_value(self.MOTOR_VELO)
        return self._velocity

    def get_precision(self):
        self._tolerance = self.get_channel_value(self.MOTOR_PREC)

    def set_velocity(self, value):
        self.set_channel_value(self.MOTOR_VELO, value)
        self._velocity = value

    def done_movement(self):
        dmov = self.get_channel_value(self.MOTOR_DMOV)
        return bool(dmov)

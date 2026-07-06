import time
from typing import Optional

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import (
    EPICSActuator,
    EPICSRestrictedMovement,
)


class EPICSMotor(EPICSActuator, AbstractMotor):
    MOTOR_DMOV = "dmov"
    MOTOR_STOP = "stop"
    MOTOR_VELO = "velo"
    MOTOR_ACCL = "accl"
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
        self.add_channel({"type": "epics", "name": self.MOTOR_ACCL}, pvname + ".ACCL")
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

    def wait_ready(self, timeout: Optional[float] = None):
        self._ready_event.clear()
        timeout = abs(self.get_value() - self.setpoint) / self.get_velocity()
        timeout += 2 * self.get_acceleration()
        # Timeout tolerance
        timeout += 10
        is_set = self._ready_event.is_set()
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while not is_set:
                    is_set = self._ready_event.is_set()
                    if self.done_movement() and not self.hasnt_arrived(self.setpoint):
                        self._ready_event.set()
                    time.sleep(0.15)
        except TimeoutError:
            pvname = self.get_channel_object("").command.pv_name
            self.print_log(
                level="error",
                msg=f"{pvname} motion has timed out.",
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
        self._tolerance = 10 ** (-self.get_channel_value(self.MOTOR_PREC))

    def set_velocity(self, value):
        self.set_channel_value(self.MOTOR_VELO, value)
        self._velocity = value

    def get_acceleration(self):
        self._acceleration = self.get_channel_value(self.MOTOR_ACCL)
        return self._acceleration

    def done_movement(self):
        dmov = self.get_channel_value(self.MOTOR_DMOV)
        return bool(dmov)


class EPICSMotorDetachable(EPICSMotor):
    """
    Class that implements an interface of motor record IOC and accepts
    a presence PV, that indicated if the motor is or is not present on the
    facility. If it is present, it actuates as an EpicsMotor, if it is not,
    then the widget receives the state OFF and remains disabled.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSMotor.EPICSMotorDetachable
    epics:
    "MOTOR_PV":
        channels:
        '':
    'PRESENCE_PREFIX':
        channels:
        'presence':
            suffix: "PRESENCE_SUFFIX"
    configuration:
    is_absent_value: 0

    """

    MOTOR_PRESENCE_RBV = "presence"

    def init(self):
        super().init()
        self.get_value()

    def check_is_absent(self):
        value = self.get_property("is_absent_value")
        current_value = int(self.get_channel_value(self.MOTOR_PRESENCE_RBV))
        return current_value == value

    def get_value(self):
        if self.check_is_absent():
            self.update_state(self.STATES.OFF)
        return super().get_value()


class ResolutionVirtualMotor(EPICSMotor):
    """
    A specific class for LNLS resolution object, such that the
    get_resolution_limits_for_energy function from EnergyAdapter
    works properly.

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSMotor.ResolutionVirtualMotor
    epics:
        "MNC:B:SoftIOC:Resolution":
            channels:
                '':
    """

    def get_limits_for_wavelength(self, wavelength):
        return self.get_limits()


class LNLSRestrictedMotor(EPICSRestrictedMovement, EPICSMotor):
    pass


class LNLSRestrictedMotorDetachable(EPICSRestrictedMovement, EPICSMotorDetachable):
    pass

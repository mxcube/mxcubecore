import time
from typing import Optional

import gevent
import numpy as np

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


class EPICSActuator(AbstractActuator):
    ACTUATOR_VAL = "val"  # setpoint
    ACTUATOR_RBV = "rbv"  # readback

    def __init__(self, name):
        super().__init__(name)
        self.setpoint = None
        self._nominal_limits = (-1e4, 1e4)
        self.default_timeout = 180
        if not self.unit:
            self.unit = 10**-3

    def init(self):
        self.update_state(self.STATES.READY)
        self.connect(self.get_channel_object("rbv"), "update", self.update_value)

    def hasnt_arrived(self, setpoint):
        readback = self.get_value()
        if not readback:
            return False
        return not np.isclose(readback, setpoint, rtol=self.unit, atol=self.unit)

    def wait_ready(self, timeout: Optional[float] = None):
        self._ready_event.clear()
        is_set = self._ready_event.is_set()
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while not is_set:
                    is_set = self._ready_event.is_set()
                    if not self.hasnt_arrived(self.setpoint):
                        self._ready_event.set()
                    time.sleep(0.15)
        except TimeoutError:
            pvname = self.get_channel_object("").command.pv_name
            self.print_log(
                level="error",
                msg=f"{pvname} motion has timed out.",
            )
        self.update_state(self.STATES.READY)

    def get_value(self):
        return self.get_channel_value(self.ACTUATOR_RBV)

    def _set_value(self, value):
        self.setpoint = value
        self.update_state(self.STATES.BUSY)
        self.set_channel_value(self.ACTUATOR_VAL, value)

    def set_value(self, value, timeout: float = 0):
        if not timeout:
            timeout = self.default_timeout
        try:
            super().set_value(value, timeout)
        except ValueError:
            pvname = self.get_channel_object("rbv").command.pv_name
            msg = f"{pvname} value {value} is outside of actuator limits"
            msg += f": {self._nominal_limits}"
            self.print_log(
                level="error",
                msg=msg,
            )

    def abort(self):
        if self._wait_task is not None:
            self._wait_task.set()
        self.update_state(self.STATES.READY)

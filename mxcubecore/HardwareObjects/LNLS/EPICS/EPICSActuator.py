import threading
import time

import gevent
import numpy as np

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


class EPICSActuator(AbstractActuator):
    ACTUATOR_VAL = "val"  # setpoint
    ACTUATOR_RBV = "rbv"  # readback

    def __init__(self, name):
        super(EPICSActuator, self).__init__(name)
        self._wait_task = None
        self.setpoint = None
        self._nominal_limits = (-1e4, 1e4)
        self.default_timeout = 180

    def init(self):
        self.update_state(self.STATES.READY)
        self.connect(self.get_channel_object("rbv"), "update", self.update_value)
        if not self.unit:
            self.unit = 10**-3

    def hasnt_arrived(self, setpoint):
        return not np.isclose(
            self.get_value(), setpoint, rtol=self.unit, atol=self.unit
        )

    def _wait_thread(self, setpoint, timeout):
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while self.hasnt_arrived(setpoint) and not self._wait_task.is_set():
                    time.sleep(0.15)
        except TimeoutError:
            pvname = self.get_channel_object("rbv").command.pv_name
            self.log(f"{pvname} motion has timed out.")
        self.update_state(self.STATES.READY)

    def wait_ready(self, timeout):
        self._wait_task = threading.Event()
        thread = threading.Thread(
            target=self._wait_thread, args=(self.setpoint, timeout)
        )
        thread.start()

    def get_value(self):
        return self.get_channel_value(self.ACTUATOR_RBV)

    def _set_value(self, value):
        self.setpoint = value
        self.update_state(self.STATES.BUSY)
        self.set_channel_value(self.ACTUATOR_VAL, value)

    def set_value(self, value, timeout: float = 0):
        if not timeout:
            timeout = self.default_timeout
        super().set_value(value, timeout)

    def abort(self):
        if self._wait_task is not None:
            self._wait_task.set()
        self.update_state(self.STATES.READY)

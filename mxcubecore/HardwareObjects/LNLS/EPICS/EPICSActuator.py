import time

import gevent
import numpy as np

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


class EPICSActuator(AbstractActuator):
    ACTUATOR_VAL = "val"  # setpoint
    ACTUATOR_RBV = "rbv"  # readback

    def __init__(self, name):
        super(EPICSActuator, self).__init__(name)
        self.__wait_actuator_task = None
        self._nominal_limits = (-1e4, 1e4)

    def init(self):
        self.update_state(self.STATES.READY)
        self.connect(self.get_channel_object("rbv"), "update", self.update_value)
        if not self.unit:
            self.unit = 10**-3

    def hasnt_arrived(self, setpoint):
        return not np.isclose(
            self.get_value(), setpoint, rtol=self.unit, atol=self.unit
        )

    def _wait_actuator(self, setpoint, timeout):
        start = time.time()
        while self.hasnt_arrived(setpoint):
            gevent.sleep(0.15)
            cur = time.time()
            if (cur - start) > timeout:
                raise TimeoutError
        self.update_state(self.STATES.READY)

    def get_value(self):
        return self.get_channel_value(self.ACTUATOR_RBV)

    def _set_value(self, value):
        self.set_channel_value(self.ACTUATOR_VAL, value)

    def set_value(self, value, timeout=0):
        if self.read_only:
            raise ValueError("Attempt to set %s for read-only Actuator" % value)
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            self._set_value(value)
            self.__wait_actuator_task = gevent.spawn(
                lambda: self._wait_actuator(value, timeout)
            )
        else:
            raise ValueError(
                "Invalid value %s; limits are %s" % (value, self.get_limits())
            )

    def abort(self):
        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)

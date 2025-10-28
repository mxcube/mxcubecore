import numpy as np
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


class EPICSActuator(AbstractActuator):
    """EPICS actuator class"""

    ACTUATOR_VAL = "val"  # setpoint
    ACTUATOR_RBV = "rbv"  # readback

    def __init__(self, name):
        super(EPICSActuator, self).__init__(name)
        self.__wait_actuator_task = None
        self._nominal_limits = (-1e4, 1e4)

    def init(self):
        """Initialization method"""
        super(EPICSActuator, self).init()
        gevent.spawn(self._watch)
        self.update_state(self.STATES.READY)
        self.old_value = None
        if not self.unit:
            self.unit = 0

    def _watch(self):
        """Watch Actuator current value and update it on the UI."""
        while True:
            gevent.sleep(0.25)
            if self._nominal_value != self.old_value:
                self.old_value = self._nominal_value
            self.update_value()

    def hasnt_arrived(self, setpoint):
        return not np.isclose(self.get_value(), setpoint, rtol=self.unit, atol=self.unit)

    def _wait_actuator(self, setpoint):
        """Wait actuator to be ready."""
        while self.hasnt_arrived(setpoint):
            gevent.sleep(0.25)
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Override AbstractActuator method."""
        return self.get_channel_value(self.ACTUATOR_RBV)

    def _set_value(self, value):
        """Override AbstractActuator method."""
        self.set_channel_value(self.ACTUATOR_VAL, value)

    def set_value(self, value, timeout=0):
        """Override AbstractActuator method."""
        """ Set actuator to value.
        Args:
            value: target value
            timeout (float): optional - timeout [s],
                            If timeout == 0: return at once and do not wait
                            (default);
                            if timeout is None: wait forever.
        Raises:
            ValueError: Invalid value or attemp to set read only actuator.
            RuntimeError: Timeout waiting for status ready  # From wait_ready
        """
        if self.read_only:
            raise ValueError("Attempt to set value for read-only Actuator")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            self._set_value(value)
            self.__wait_actuator_task = gevent.spawn(lambda: self._wait_actuator(value))
        else:
            raise ValueError(
                "Invalid value %s; limits are %s" % (value, self.get_limits())
            )

    def abort(self):
        """Imediately halt movement. By default self.stop = self.abort"""
        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)


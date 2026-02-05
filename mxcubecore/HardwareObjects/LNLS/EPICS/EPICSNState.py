import gevent
import threading
import time
from enum import Enum
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum


class EPICSNState(EPICSActuator, AbstractNState):

    def init(self):
        super().init()
        limits = self._nominal_limits
        self.set_limits(limits)
        self._initialise_values()
        current_value = self.get_value()
        self.update_value(current_value)
        self.update_state(self.STATES.READY)

    def wait_ready(self, timeout):
        self._wait_task = threading.Event()
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while (
                    self.setpoint != EPICSActuator.get_value(self) and not self._wait_task.is_set()
                ):
                    time.sleep(0.15)
        except TimeoutError:
            pvname = self.get_channel_object("rbv").command.pv_name
            self.print_log(level="error", msg=f"Motion has timed out.")
        self.update_state(self.STATES.READY)

    def _set_value(self, value):
        if isinstance(value, Enum):
            value = value.value
        EPICSActuator._set_value(self, value)

    def get_value(self):
        value = EPICSActuator.get_value(self)
        return self.value_to_enum(value)

    def _initialise_values(self):
        low, high = self.get_limits()
        values = self.get_property("values")
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def update_value(self, value=None) -> None:
        value = self.value_to_enum(value)
        super().update_value(value)

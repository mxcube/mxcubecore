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

    def _set_value(self, value):
        if isinstance(value, Enum):
            value = value.value
        EPICSActuator._set_value(self, value)

    def get_value(self):
        value = EPICSActuator.get_value(self)
        if not isinstance(value, Enum):
            value = self.value_to_enum(value)
        return value

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

    def hasnt_arrived(self, setpoint):
        if not isinstance(setpoint, Enum):
            setpoint = self.value_to_enum(setpoint)
        readback = self.get_value()
        if not readback:
            return False
        return setpoint != readback
from enum import Enum
import gevent
import time

from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSNState import EPICSNState


class LNLSZoom(EPICSNState):

    def init(self):
        EPICSNState.init(self)
        self.initialise_values()
        limits = (1, 8)
        self.set_limits(limits)
        self._initialise_values()
        self.update_limits(limits)
        current_value = self.get_value()
        self.update_value(current_value)
        self.update_state(self.STATES.READY)

    def set_limits(self, limits=(None, None)):
        self._nominal_limits = limits

    def update_limits(self, limits=None):
        if limits is None:
            limits = self.get_limits()

        self._nominal_limits = limits
        self.emit("limitsChanged", (limits,))

    def _initialise_values(self):
        low, high = self.get_limits()

        values = {"LEVEL%s" % str(v): v for v in range(low, high + 1)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def _move(self, value):
        """Override super class method."""
        self.update_state(self.STATES.BUSY)
        time.sleep(0.2)
        self.update_state(self.STATES.READY)
        current_value = self.get_value()
        self.update_value(current_value)
        return value

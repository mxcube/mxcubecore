from enum import Enum
import gevent
import time

from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSNState import EPICSNState


class LNLSZoom(EPICSNState):
    """MicrodiffZoomMockup class"""

    def __init__(self, name):
        super(LNLSZoom, self).__init__(name)

    def init(self):
        """Initialize the zoom"""
        EPICSNState.init(self)

        self.initialise_values()
        _len = len(self.VALUES) - 1
        if _len > 0:
            # we can only assume that the values are consecutive integers
            # so the limits correspond to the keys
            limits = (1, _len)
            self.set_limits(limits)
        else:
            # Normally we get the limits from the hardware
            limits = (1, 8)
            self.set_limits(limits)
            # there is nothing in the xml file, create ValueEnum from the limits
            self._initialise_values()

        self.update_limits(limits)
        current_value = self.get_value()
        self.update_value(current_value)
        self.update_state(self.STATES.READY)

    def set_limits(self, limits=(None, None)):
        """Overrriden from AbstractActuator"""
        self._nominal_limits = limits

    def update_limits(self, limits=None):
        """Overrriden from AbstractNState"""
        if limits is None:
            limits = self.get_limits()

        self._nominal_limits = limits
        self.emit("limitsChanged", (limits,))

    def _initialise_values(self):
        """Initialise the ValueEnum"""
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

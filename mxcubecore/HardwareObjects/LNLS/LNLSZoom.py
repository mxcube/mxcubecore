"""
Example xml file
<object class="LNLSZoom">
  <username>zoom</username>
  <actuator_name>zoom</actuator_name>
  <exporter_address>130.235.94.124:9001</exporter_address>
  <values>{"LEVEL1": 1, "LEVEL2": 2, "LEVEL3": 3, "LEVEL4": 4, "LEVEL5": 5, "LEV
EL6": 6}</values>
</object>
"""
import time
from enum import Enum

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractNState import (
    AbstractNState,
    BaseValueEnum,
)
from mxcubecore.HardwareObjects.LNLS.EPICSActuator import EPICSActuator


class LNLSZoom(EPICSActuator, AbstractNState):
    """MicrodiffZoomMockup class"""

    def __init__(self, name):
        super(LNLSZoom, self).__init__(name)

    def init(self):
        """Initialize the zoom"""
        EPICSActuator.init(self)
        AbstractNState.init(self)

        self.initialise_values()
        _len = len(self.VALUES) - 1
        if _len > 0:
            # we can only assume that the values are consecutive integers
            # so the limits correspond to the keys
            limits = (1, _len)
            self.set_limits(limits)
        else:
            # Normally we get the limits from the hardware
            limits = (1, 10)
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
        """Initialise the ValueEnum """
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

    def get_value(self):
        """Override super class method."""
        current_val = super(LNLSZoom, self).get_value()
        current_enum = self.value_to_enum(current_val)
        return current_enum

    def _set_value(self, value):
        """Override super class method."""
        enum = value
        target_val = enum.value
        super(LNLSZoom, self)._set_value(target_val)

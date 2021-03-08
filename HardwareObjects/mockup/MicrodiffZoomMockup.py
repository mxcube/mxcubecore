"""
Example xml file
<object class="MicrodiffZoomMockup">
  <username>zoom</username>
  <actuator_name>zoom</actuator_name>
  <exporter_address>130.235.94.124:9001</exporter_address>
  <values>{"LEVEL1": 1, "LEVEL2": 2, "LEVEL3": 3, "LEVEL4": 4, "LEVEL5": 5, "LEV
EL6": 6}</values>
</object>
"""
from enum import Enum
import gevent

from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum


class MicrodiffZoomMockup(AbstractNState):
    """MicrodiffZoomMockup class"""

    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def init(self):
        """Initialize the zoom"""
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

        # we assume that the names are LEVEL%d, starting from 1
        self.update_value(self.VALUES.LEVEL1)

        self.update_state(self.STATES.READY)

    def _set_zoom(self, value):
        """
        Simulated motor movement.
        """
        self.update_state(self.STATES.BUSY)
        gevent.sleep(0.2)
        self.update_value(value)
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

    def _set_value(self, value):
        """Overrriden from AbstractActuator"""
        gevent.spawn(self._set_zoom, value)

    def get_value(self):
        """Overrriden from AbstractActuator"""
        return self._nominal_value

    def _initialise_values(self):
        """Initialise the ValueEnum """
        low, high = self.get_limits()

        values = {"LEVEL%s" % str(v): v for v in range(low, high + 1)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

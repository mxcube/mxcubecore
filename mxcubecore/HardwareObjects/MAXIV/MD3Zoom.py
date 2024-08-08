from enum import Enum
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState


class MD3Zoom(ExporterNState):
    """BIOMAX and MICROMAX MicrodiffZoom class"""

    def __init__(self, name):
        super().__init__(name)

    def init(self):
        """Initialize the zoom"""
        super().init()
        level = self.get_property("level", "")

        limits = (0, level - 2)
        self.set_limits(limits)
        self._initialise_values()

    def set_limits(self, limits=(None, None)):
        """Overrriden from AbstractActuator"""
        self._nominal_limits = limits

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
        """
        super().update_value()

    def update_limits(self, limits=None):
        """Overrriden from AbstractNState"""
        if limits is None:
            limits = self.get_limits()
        self._nominal_limits = limits
        self.emit("limitsChanged", (limits,))

    def _initialise_values(self):
        """Initialise the ValueEnum"""
        low, high = self.get_limits()
        values = {"LEVEL%s" % str(v): v for v in range(low + 1, high + 2)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

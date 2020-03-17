# from MD2Motor import MD2Motor
from HardwareRepository.HardwareObjects.ExporterNState import ExporterNState
import logging
import math
import ast
import enum
import time

class MicrodiffZoomMockup(ExporterNState):
    """MicrodiffZoom Mockup class"""

    def __init__(self, name):
        super(MicrodiffZoomMockup, self).__init__(name)
        self.predefined_positions = {}
        self._exporter = None
        self._limits = None
        self.position_channel = None
        self.motor_state = None

    def init(self):
        """Initialize the zoom"""
        #ExporterNState.init(self)
        values = ast.literal_eval(self.getProperty("values"))
        self._nominal_limits = (values[0], values[-1])

        values = { ("LEVEL%s" % str(values.index(v) + 1)):v for v in values }
        values.update({"UNKNOWN": 0})

        self.VALUES = enum.Enum("MICRODIFF_ZOOM_ENUM", values)
        self._value = self.VALUES.LEVEL1
        self.update_state()

    def get_limits(self):
        """Returns zoom low and high limits.
        Returns:
            (tuple): two int tuple (low limit, high limit).
        """
        return self._nominal_limits

    def get_state(self, state=None):
        return self._state

    def _set_value(self, enum_var):
        """Set device to value of enum_var

        Args:
            value (enum): enum variable
        """
        self.update_state(self.STATES.BUSY)
        time.sleep(0.3)
        self._value = enum_var
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Get the device value
        Returns:
            (str): The name of the enum variable
        """
        return self._value
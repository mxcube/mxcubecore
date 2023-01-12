from enum import Enum
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum


class MICROMAXZoom(AbstractNState):
    """BIOMAXMicrodiffZoom class"""

    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def init(self):
        """Initialize the zoom"""
        AbstractNState.init(self)
        self.actuator_name = self.get_property("actuator_name", "")
        level = self.get_property("level", "")
        self.value_channel_name = self.get_property("value_channel_name", "")
        self.predefined_position_attr = self.add_channel({"type":"exporter", "name": self.actuator_name  }, self.value_channel_name)
        self.connect(
                    self.predefined_position_attr, "update", self.value_changed
                )
        self.motors_state_attr = self.add_channel({"type":"exporter", "name":self.actuator_name}, "states")
        self.connect(
                    self.predefined_position_attr, "update", self.state_changed
                )

        limits = (0, level-2)
        self.set_limits(limits)
        self._initialise_values()
        self.update_limits(limits)

        self.update_state(self.STATES.READY)

    def _set_zoom(self, value):
        """
        Simulated motor movement.
        """
        gevent.sleep(1)
        if value == None:
            value = self.VALUES.LEVEL1
        self.predefined_position_attr.set_value(self.VALUES(value).value)
        self.update_value(self.VALUES(value))
        self.update_state(self.get_state())

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
        self.re_emit_values()

    def get_value(self):
        """Overrriden from AbstractActuator"""
        return self._nominal_value

    def _initialise_values(self):
        """Initialise the ValueEnum """
        low, high = self.get_limits()
        values = {"LEVEL%s" % str(v): v for v in range(low+1, high+2)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def value_changed(self, value):
        self.update_value(self.VALUES(value))
        self.emit("predefinedPositionChanged", (self.get_value(),0))

    def state_changed(self, value):
        self.emit("stateChanged", (self.get_state(),))

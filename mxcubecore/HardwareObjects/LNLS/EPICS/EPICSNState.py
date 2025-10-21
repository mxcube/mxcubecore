from enum import Enum
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator


class EPICSNState(EPICSActuator, AbstractNState):
    """Microdiff with Exporter implementation of AbstartNState"""

    def __init__(self, name):
        self.__wait_actuator_task = None
        AbstractNState.__init__(self, name)
        EPICSActuator.__init__(self, name)

    def init(self):
        """Initialise the device"""
        AbstractNState.init(self)
        EPICSActuator.init(self)

    def _wait_actuator(self, setpoint):
        """Wait timeout seconds till status is ready.
        Args:
            timeout(float): Timeout [s]. None means infinite timeout.
        """
        enum_setpoint = self.value_to_enum(setpoint)
        while enum_setpoint != self.get_value():
            gevent.sleep(0.25)
        self.update_state(self.STATES.READY)

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        self.update_state(self.STATES.BUSY)

        if isinstance(value, Enum):
            if isinstance(value.value, (tuple, list)):
                value = value.value[0]
            else:
                value = value.value

        EPICSActuator._set_value(self, value)

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """
        value = EPICSActuator.get_value(self)
        return self.value_to_enum(value)

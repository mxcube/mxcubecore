import gevent
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator


class EPICSNState(EPICSActuator, AbstractNState):

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
        if isinstance(value, Enum):
            value = value.value
        EPICSActuator._set_value(self, value)

    def get_value(self):
        value = EPICSActuator.get_value(self)
        return self.value_to_enum(value)

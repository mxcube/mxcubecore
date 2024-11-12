from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.ExporterMotor import ExporterMotor


class MicrodiffLight(ExporterMotor):
    def __init__(self, name):
        ExporterMotor.__init__(self, name)
        self._motor_pos_suffix = "Level"

    def init(self):
        ExporterMotor.init(self)
        try:
            _low, _high = self.get_property("limits").split(",")
            self._limits = (float(_low), float(_high))
        except (AttributeError, TypeError, ValueError):
            self._limits = (0, 10)
        self.chan_light_is_on = self.get_channel_object("chanLightIsOn")
        self.update_state(self.STATES.READY)

    def get_state(self):
        """Get the light state as a motor.
        Returns:
            (enum 'HardwareObjectState'): Light state.
        """
        return self._state

    def get_limits(self):
        return self._limits

    def light_is_out(self):
        return self.chan_light_is_on.get_value()

    def move_in(self):
        self.chan_light_is_on.set_value(True)

    def move_out(self):
        self.chan_light_is_on.set_value(False)

    def _set_value(self, value):
        """Move motor to absolute value.
        Args:
            value (float): target value
        """
        self.update_state(self.STATES.BUSY)
        self.motor_position_chan.set_value(value)
        self.update_state(self.STATES.READY)

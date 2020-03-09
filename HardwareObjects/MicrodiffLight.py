from HardwareRepository.HardwareObjects.ExporterMotor import ExporterMotor
from HardwareRepository.BaseHardwareObjects import HardwareObjectState


class MicrodiffLight(ExporterMotor):
    def __init__(self, name):
        ExporterMotor.__init__(self, name)
        self._motor_pos_suffix = "Level"

    def init(self):
        ExporterMotor.init(self)
        try:
            _low, _high = self.getProperty("limits").split(",")
            self._limits = (float(_low), float(_high))
        except (AttributeError, TypeError, ValueError):
            self._limits = (0, 10)
        self.chan_light_is_on = self.getChannelObject("chanLightIsOn")

    def set_value(self, value, wait=False):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target value
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        ExporterMotor._set_value(self, value)
        self.update_value(value)
        self.update_state()

    def get_state(self):
        """Get the light state as a motor.
        Returns:
            (enum 'HardwareObjectState'): Light state.
        """
        return HardwareObjectState.READY

    def get_limits(self):
        return self._limits

    def light_is_out(self):
        return self.chan_light_is_on.get_value()

    def move_in(self):
        self.chan_light_is_on.set_value(True)

    def move_out(self):
        self.chan_light_is_on.set_value(False)

from HardwareRepository.HardwareObjects.ExpMotor import ExpMotor
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import MotorStates

class MicrodiffLight(ExpMotor):
    def __init__(self, name):
        ExpMotor.__init__(self, name)
        self._motor_pos_suffix = "Factor"

    def init(self):
        ExpMotor.init(self)
        try:
            _low,_high = self.getProperty("limits").split(',')
            self._limits = (float(_low), float(_high))
        except (AttributeError, TypeError, ValueError):
            self._limits = (0, 2)
        self.chan_light_is_on = self.getChannelObject("chanLightIsOn")

    def get_state(self):
        """Get the light state as a motor.
        Returns:
            (enum 'MotorStates'): Motor state.
        """
        return MotorStates.READY

    def get_limits(self):
        return self._limits

    def update_position(self, position):
        if position is None:
            position = self.get_position()
        self.position = position
        self.emit("positionChanged", (self.position,))

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.update_position(self.get_position())
        elif signal == "limitsChanged":
            self.update_limits(self.get_limits())

    def light_is_out(self):
        return self.chan_light_is_on.get_value()

    def move_in(self):
        self.chan_light_is_on.set_value(False)

    def move_out(self):
        self.chan_light_is_on.set_value(True)

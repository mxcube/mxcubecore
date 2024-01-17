from mxcubecore.HardwareObjects.ExporterMotor import ExporterMotor

"""You may need to import monkey when you test standalone"""
# from gevent import monkey
# monkey.patch_all(thread=False)


class MICROMAXLight(ExporterMotor):
    """Class for MD3 Light devices."""

    def __init__(self, name):
        ExporterMotor.__init__(self, name)

    def init(self):
        ExporterMotor.init(self)
        _low, _high = self.get_property("limits").split(",")
        self._limits = (float(_low), float(_high))

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

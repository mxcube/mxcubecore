import logging
from mxcubecore.HardwareObjects.abstract.AbstractResolution import AbstractResolution
from mxcubecore import HardwareRepository as HWR
from resolution import resolution
from beam_center import beam_center


class PX2Resolution(AbstractResolution):
    def __init__(self, name):
        super(PX2Resolution, self).__init__(name)
        self.resolution_motor = resolution()
        self.beam_center = beam_center()
        
    def connect_notify(self, signal):
        if signal == "stateChanged":
            self.update_state(self.get_state())

    def get_value(self):
        self._nominal_value = self.resolution_motor.get_resolution()
        return self._nominal_value
    
    def _set_value(self, value):
        self.resolution_motor.set_resolution(value)

    def get_beam_centre(self, dtox=None):
        return self.beam_center.get_beam_center()

    def get_limits(self):
        return self.resolution_motor.get_resolution_limits()

    def stop(self):
        self.resolution_motor.stop()

    def is_ready(self):
        return True

    def update_distance(self, value=None):
        """Update the resolution when distance changed.
        Args:
            value (float): Detector distance [mm].
        """
        self._nominal_value = self.resolution_motor.get_resolution()
        self.emit("valueChanged", (self._nominal_value,))

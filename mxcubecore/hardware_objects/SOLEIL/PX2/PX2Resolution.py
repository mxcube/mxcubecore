import logging
from mxcubecore.hardware_objects.Resolution import Resolution
from resolution import resolution
from beam_center import beam_center


class PX2Resolution(Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.__init__(self, *args, **kwargs)

    def init(self):

        self.resolution_motor = resolution()
        self.beam_center = beam_center()

        self.energy_channel = self.get_channel_object("energy")
        self.energy_channel.connect_signal("update", self.update_resolution)

        self.energy_state_channel = self.get_channel_object("energy_state")
        self.energy_state_channel.connect_signal("update", self.update_energy_state)

        self.detector_distance_channel = self.get_channel_object("detector_position")
        self.energy_channel.connect_signal("update", self.update_resolution)
        self.energy_channel.connect_signal("valueChanged", self.update_resolution)
        self.detector_distance_channel.connect_signal("update", self.update_resolution)

        self.detector_position_state_channel = self.get_channel_object(
            "detector_position_state"
        )
        self.detector_position_state_channel.connect_signal(
            "update", self.update_detector_position_state
        )

        self.det_width = self.get_property("detector_width")
        self.det_height = self.get_property("detector_height")

    def connect_notify(self, signal):
        if signal == "stateChanged":
            self.dtoxStateChanged(self.get_state())

    def _set_value(self, value):
        self.resolution_motor.set_resolution(value)

    def get_state(self):
        return self.detector_position_state_channel.value

    def get_beam_centre(self, dtox=None):
        return self.beam_center.get_beam_center()

    def get_limits(self):
        return self.resolution_motor.get_resolution_limits()

    def dtoxStateChanged(self, state=None):
        self.update_detector_position_state()

    def update_detector_position_state(self, state=None):
        self.emit("stateChanged", state)

    def update_energy_state(self, state=None):
        self.emit("stateChanged", state)

    def update_resolution(self, values=None):
        # logging.getLogger("HWR").info('update_resolution values: %s' % str(values))
        # logging.getLogger('HWR').info('energy %s' % str(self.energy_channel.value))
        # logging.getLogger('HWR').info('detector_distance %s' % str(self.detector_distance_channel.value))
        self._nominal_value = self.resolution_motor.get_resolution()
        self.emit("valueChanged", self._nominal_value)
        self.emit("statechanged", self.get_state())

    def stop(self):
        self.resolution_motor.stop()

import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class ALBASupervisor(HardwareObject):
    def __init__(self, *args):
        super().__init__(*args)

    def init(self):
        self.state_chan = self.get_channel_object("state")
        self.go_collect_cmd = self.get_command_object("go_collect")
        self.go_sample_view_cmd = self.get_command_object("go_sample_view")
        self.go_transfer_cmd = self.get_command_object("go_transfer")
        self.go_beam_view_cmd = self.get_command_object("go_beam_view")

        self.phase_chan = self.get_channel_object("phase")
        self.detector_cover_chan = self.get_channel_object("detector_cover_open")

        self.state_chan.connect_signal("update", self.state_changed)
        self.phase_chan.connect_signal("update", self.phase_changed)
        self.detector_cover_chan.connect_signal("update", self.detector_cover_changed)

    def is_ready(self):
        return True

    def getUserName(self):
        return self.username

    def state_changed(self, value):
        self.current_state = value
        self.emit("stateChanged", self.current_state)

    def phase_changed(self, value):
        if value == "Sample":
            value = "Centring"
        self.current_phase = value
        self.emit("phaseChanged", self.current_phase)

    def get_current_phase(self):
        return self.phase_chan.get_value()

    def go_collect(self):
        return self.go_collect_cmd()

    def go_transfer(self):
        return self.go_transfer_cmd()

    def go_sample_view(self):
        return self.go_sample_view_cmd()

    def go_beam_view(self):
        return self.go_beam_view_cmd()

    def get_state(self):
        return self.state_chan.get_value()

    def detector_cover_changed(self, value):
        self.detector_cover_opened = value
        # self.emit('levelChanged', self.current_level)

    def open_detector_cover(self):
        self.detector_cover_chan.set_value(True)

    def close_detector_cover(self, value):
        self.detector_cover_chan.set_value(False)

    def is_detector_cover_opened(self):
        return self.detector_cover_chan.get_value()


def test_hwo(hwo):
    print('\nSupervisor control "%s"\n' % hwo.getUserName())
    print("   Detector Cover  opened:", hwo.is_detector_cover_opened())
    print("   Current Phase is:", hwo.get_current_phase())
    print("   Current State is:", str(hwo.get_state()))

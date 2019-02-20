"""
[Name] EMBLImageTracking

[Description] Hardware object used to control image tracking
By default ADXV is used

[Emited signals]

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
"""

import logging
from HardwareRepository.BaseHardwareObjects import Device


class EMBLImageTracking(Device):
    def __init__(self, *args):
        Device.__init__(self, *args)

        self.target_ip = None
        self.target_port = None
        self.state = None
        self.active_socket = None
        self.state_dict = {"image_tracking": False, "filter_frames": False}

        self.chan_state = None
        self.chan_enable_image_tracking = None
        self.cmd_load_image = None

    def init(self):
        self.chan_enable_image_tracking = self.getChannelObject(
            "chanImageTrackingEnabled"
        )
        self.chan_enable_image_tracking.connectSignal(
            "update", self.image_tracking_enable_state_changed
        )
        self.chan_filter_frames = self.getChannelObject("chanFilterFramesEnabled")
        if self.chan_filter_frames is not None:
            self.chan_filter_frames.connectSignal(
                "update", self.filter_frames_enabled_changed
            )

        self.chan_state = self.getChannelObject("chanState")
        self.chan_state.connectSignal("update", self.state_changed)

        self.cmd_load_image = self.getCommandObject("cmdLoadImage")

    def image_tracking_enable_state_changed(self, state):
        self.state_dict["image_tracking"] = state
        self.emit("imageTrackingStateChanged", (self.state_dict,))

    def filter_frames_enabled_changed(self, state):
        self.state_dict["filter_frames"] = state
        self.emit("imageTrackingStateChanged", (self.state_dict,))

    def state_changed(self, state):
        if self.state != state:
            self.state = state
        self.emit("stateChanged", (self.state,))

    def is_tracking_enabled(self):
        return self.chan_enable_image_tracking.getValue()

    def set_image_tracking_state(self, state):
        self.chan_enable_image_tracking.setValue(state)

    def set_filter_frames_state(self, state):
        self.chan_filter_frames.setValue(state)

    def load_image(self, image_name):
        if self.is_tracking_enabled():
            self.set_image_tracking_state(False)
        self.cmd_load_image(str(image_name))

    def update_values(self):
        self.emit("stateChanged", self.state)
        self.emit("imageTrackingStateChanged", (self.state_dict,))

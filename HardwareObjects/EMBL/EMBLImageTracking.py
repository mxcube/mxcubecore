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
    """
    Description:
    """  	

    def __init__(self, *args):
        """
        Descrip. :
        """
        Device.__init__(self, *args)

        self.target_ip = None
        self.target_port = None
        self.image_tracking_enabled = None
        self.state = None
        self.active_socket = None

        self.chan_state = None
        self.chan_enable_image_tracking = None
        self.cmd_load_image = None
        

    def init(self):
        """
        Descript. : 
        """
        self.chan_enable_image_tracking = self.getChannelObject("chanEnableImageTracking")
        self.chan_enable_image_tracking.connectSignal("update", self.enable_image_tracking_changed)
        
        self.chan_state = self.getChannelObject("chanState")
        self.chan_state.connectSignal("update", self.state_changed) 
        
        self.cmd_load_image = self.getCommandObject("cmdLoadImage")

    def enable_image_tracking_changed(self, state):
        self.image_tracking_enabled = state 
        self.emit("imageTrackingEnabledChanged", (self.image_tracking_enabled, ))

    def state_changed(self, state):
        if self.state != state:
            self.state = state
        self.emit("stateChanged", (self.state, ))

    def is_tracking_enabled(self):
        if self.chan_enable_image_tracking is not None:
            return self.chan_enable_image_tracking.getValue() 

    def set_image_tracking_state(self, state):
        if self.chan_enable_image_tracking is not None: 
            self.chan_enable_image_tracking.setValue(state)  

    def load_image(self, image_name):
        if self.image_tracking_enabled:
            self.set_image_tracking_state(False)
        self.cmd_load_image(str(image_name))

    def update_values(self):
        self.emit("stateChanged", self.state)

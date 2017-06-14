"""
[Name] ImageTracking

[Description] Hardware object used to control image tracking
By default ADXV is used

[Emited signals]

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
"""

import socket
import logging
from HardwareRepository.BaseHardwareObjects import Device

class ImageTracking(Device):
    """
    Description:
    """  	

    def __init__(self, *args):
        """
        Descrip. :
        """
        Device.__init__(self, *args)

        self.target_host = None
        self.target_port = None
        self.state = None

        self.chan_state = None
        self.chan_enable_image_tracking = None

    def init(self):
        """
        Descript. : 
        """
        self.chan_enable_image_tracking = self.getChannelObject("chanEnableImageTracking")

        self.chan_state = self.getChannelObject("chanState")
        if self.chan_state is not None:
            self.chan_state.connectSignal("update", self.state_changed) 
        
        try:
           self.target_ip = self.getProperty("targetIP")
        except:
           self.target_ip = socket.gethostbyname(socket.gethostname())
        
        try:
           self.target_port = int(self.getProperty("targetPort"))
        except:
           self.target_port = 8100 

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
        active_socket = socket.socket()
        active_socket.connect((self.target_ip, self.target_port))
        active_socket.send("load_image %s\n" %image_name)
        active_socket.close() 

    def update_values(self):
        self.emit("stateChanged", (self.state, ))

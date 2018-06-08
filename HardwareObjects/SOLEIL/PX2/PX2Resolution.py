import logging
from Resolution import Resolution
from resolution import resolution
from beam_center import beam_center

class PX2Resolution(Resolution):

    def __init__(self, *args, **kwargs):
        Resolution.__init__(self, *args, **kwargs)

    def init(self):
        
        self.resolution_motor = resolution()
        self.beam_center = beam_center()
        
        self.currentResolution = None
        
        self.energy_channel = self.getChannelObject("energy")
        self.energy_channel.connectSignal("update", self.update_resolution)
        
        self.energy_state_channel = self.getChannelObject("energy_state")
        self.energy_state_channel.connectSignal("update", self.update_energy_state)
        
        self.detector_distance_channel = self.getChannelObject("detector_position")
        self.energy_channel.connectSignal("update", self.update_resolution)
        self.energy_channel.connectSignal("valueChanged", self.update_resolution)
        self.detector_distance_channel.connectSignal("update", self.update_resolution)
        
        self.detector_position_state_channel = self.getChannelObject("detector_position_state")
        self.detector_position_state_channel.connectSignal("update", self.update_detector_position_state)
        
        self.energy = self.getObjectByRole("energy")
        self.dtox = self.getObjectByRole("detector_distance")
        
        self.det_radius = self.getProperty("detector_radius")
        self.det_width = self.getProperty("detector_width")
        self.det_height = self.getProperty("detector_height")
    
    def get_limits(self):
        return self.getLimits()
    
    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.dtoxStateChanged(self.getState())
    
    def move(self, resolution):
        self.resolution_motor.set_resolution(resolution)
    
    def getState(self):
        return self.detector_position_state_channel.value
    
    def get_beam_centre(self, dtox=None):
        return self.beam_center.get_beam_center()
    
    def getLimits(self):
        return self.resolution_motor.get_resolution_limits()
        
    def dtoxStateChanged(self, state=None):
        self.update_detector_position_state()
        
    def update_detector_position_state(self, state=None):
        self.emit("stateChanged", state)
        
    def update_energy_state(self, state=None):
        self.emit("stateChanged", state)
        
    def update_resolution(self, values=None):
        #logging.getLogger("HWR").info('update_resolution values: %s' % str(values))
        #logging.getLogger('HWR').info('energy %s' % str(self.energy_channel.value))
        #logging.getLogger('HWR').info('detector_distance %s' % str(self.detector_distance_channel.value))
        self.currentResolution = self.resolution_motor.get_resolution()
        self.emit("positionChanged", self.currentResolution)
        self.emit("valueChanged", self.currentResolution)
        self.emit("statechanged", self.getState())
    
    def stop(self):
        self.resolution_motor.stop()
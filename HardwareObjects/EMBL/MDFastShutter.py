import logging
from HardwareRepository.BaseHardwareObjects import Device

class MDFastShutter(Device):
    shutterState = {
        3: 'unknown',
        1: 'closed',
        0: 'opened',
        46: 'disabled'} 

    def __init__(self, name):
        Device.__init__(self, name)
        self.chan_shutter_state = None
        self.chan_current_phase = None

        self.states_dict = None
        self.state = None
        self.current_phase = None 

    def init(self):
        self.states_dict = {False: "closed",
                            True: "opened"}

        self.chan_current_phase = self.getChannelObject("chanCurrentPhase")
        if self.chan_current_phase is not None:
            self.current_phase = self.chan_current_phase.getValue()
            self.connect(self.chan_current_phase, "update", self.current_phase_changed)

        self.chan_shutter_state = self.getChannelObject("chanShutterState")
        if self.chan_shutter_state:
            self.chan_shutter_state.connectSignal("update", self.shutter_state_changed)

    def shutter_state_changed(self, value):
        if self.current_phase == "BeamLocation":
            self.state = self.states_dict.get(value, "unknown")
        else:
            self.state = "disabled"
        self.emit('shutterStateChanged', (self.state, self.state.title()))

    def current_phase_changed(self, value):
        self.current_phase = value
        if self.chan_shutter_state: 
            self.shutter_state_changed(self.chan_shutter_state.getValue()) 
    
    def getShutterState(self):
        self.shutter_state_changed(self.chan_shutter_state.getValue())
        return self.state

    def openShutter(self, wait=True):
        self.chan_shutter_state.setValue(True) 

    def closeShutter(self, wait=True):
        self.chan_shutter_state.setValue(False)


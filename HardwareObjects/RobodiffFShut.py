import logging
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.dispatcher import *

class RobodiffFShut(Equipment):
    def __init__(self, name):
        Equipment.__init__(self, name)

    def init(self):
        self.robodiff = self.getObjectByRole("robot")
        self.connect(self.robodiff.controller.fshut, "state", self.valueChanged)
        self.wagoState = "unknown"

    def connectNotify(self, signal):
        if signal=='wagoStateChanged':
           self.getWagoState(read=True)

    def valueChanged(self, value): 
        if value == "CLOSED":
            self.wagoState = 'out'
        elif value == "OPENED":
            self.wagoState = 'in'
        else:
            self.wagoState = "unknown"
        self.emit('wagoStateChanged', (self.wagoState, ))
        
    def getWagoState(self, read=False):
        if read:
          self.valueChanged(self.robodiff.controller.fshut.state())
        return self.wagoState 

    def wagoIn(self):
        self.robodiff.controller.fshut.open()
        self.getWagoState(read=True)
           
    def wagoOut(self):  
        self.robodiff.controller.fshut.close()
        self.getWagoState(read=True)
           

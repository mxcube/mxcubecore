from HardwareRepository.BaseHardwareObjects import Device
import logging

class ShutterMockup(Device):
    shutterState = {
        0: 'unknown',
        3: 'closed',
        4: 'opened',
        9: 'moving',
        17: 'automatic',
        23: 'fault',
        46: 'disabled',
        -1: 'error'
        }
  
    def __init__(self, name):
        Device.__init__(self, name)

        self.shutterStateValue = 3
        self.getWagoState = self.getShutterState
        self.state_value_str = ShutterMockup.shutterState[self.shutterStateValue]

    def init(self):
        self.setIsReady(True)
        
    def valueChanged(self, value):
        self.shutterStateValue = value
        self.state_value_str = ShutterMockup.shutterState[self.shutterStateValue]
        self.emit('shutterStateChanged', (ShutterMockup.shutterState[self.shutterStateValue], ))
       
    def getShutterState(self):
        return ShutterMockup.shutterState[self.shutterStateValue] 

    def shutterIsOpen(self):
        return True        

    def isShutterOk(self):
        return True

    def openShutter(self):
        self.valueChanged(4)

    def closeShutter(self):
        self.valueChanged(3)

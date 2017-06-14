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

        self.shutterStateValue = 0
        self.getWagoState = self.getShutterState

    def init(self):
        self.setIsReady(True)
        
    def valueChanged(self, deviceName, value):
        self.shutterStateValue = value
        self.emit('shutterStateChanged', (TempShutter.shutterState[self.shutterStateValue], ))
       
    def getShutterState(self):
        return ShutterMockup.shutterState[self.shutterStateValue] 

    def shutterIsOpen(self):
	return True        

    def isShutterOk(self):
	return True

    def openShutter(self):
	self.shutterStateValue = 4
	self.emit('shutterStateChanged', (ShutterMockup.shutterState[self.shutterStateValue], ))

    def closeShutter(self):
	self.shutterStateValue = 3
        self.emit('shutterStateChanged', (ShutterMockup.shutterState[self.shutterStateValue], ))

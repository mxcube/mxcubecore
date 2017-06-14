import logging
from HardwareRepository.BaseHardwareObjects import Device

class TangoInOut(Device):

    def __init__(self, name):
        Device.__init__(self, name)
        self.currentState = "unknown"

    def init(self):
        self.attrchan = self.getChannelObject("attributeName")
        self.attrchan.connectSignal("update", self.valueChanged)

        self.attrchan.connectSignal("connected", self._setReady)
        self.attrchan.connectSignal("disconnected", self._setReady)

        self._setReady()

        try:
	   self.inversed = self.getProperty("inversed")
        except:
	   self.inversed = False

        if self.inversed:
           self.states = ["in", "out"]
        else:
           self.states = ["out", "in"]

    def _setReady(self):
        self.setIsReady(self.attrchan.isConnected()) 

    def connectNotify(self, signal):
        if self.isReady():
           self.valueChanged(self.attrchan.getValue())


    def valueChanged(self, value):
        self.currentState = value

        if value:
            self.currentState = self.states[1]
        else:
            self.currentState = self.states[0]
        
        self.emit('wagoStateChanged', (self.currentState, ))
        
    def getWagoState(self):
        return self.currentState 

    def wagoIn(self):
        self.setIn()

    def setIn(self):
        self._setReady()
        if self.isReady():
          if self.inversed:
            self.attrchan.setValue(False)
          else:
            self.attrchan.setValue(True)
 
    def wagoOut(self):
        self.setOut()

    def setOut(self):
        self._setReady()
        if self.isReady():
          if self.inversed:
            self.attrchan.setValue(True)
          else:
            self.attrchan.setValue(False)
           

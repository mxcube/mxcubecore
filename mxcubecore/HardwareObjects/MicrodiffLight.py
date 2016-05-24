from HardwareRepository.BaseHardwareObjects import Device
import math
import logging
import time

class MicrodiffLight(Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

    def __init__(self, name):
        Device.__init__(self, name)
        self.limits = None 
        self.state = None

    def init(self): 
        self.state = MicrodiffLight.READY
        try:
           self.limits = eval(self.getProperty("limits"))
        except:
           self.limits = (0, 2)

        self.position_attr = self.getChannelObject("chanLightValue")
        if self.position_attr:
            self.position_attr.connectSignal("update", self.motorPositionChanged)

        self.chan_light_is_on = self.getChannelObject("chanLightIsOn")

        self.setIsReady(True)

    def connectNotify(self, signal):
        if self.position_attr.isConnected():
            if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
            elif signal == 'limitsChanged':
                self.motorLimitsChanged()  

    def isReady(self):
        return True
 
    def updateState(self):
        self.setIsReady(True)
 
    def getState(self):
        return self.state
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        return self.limits
 
    def motorPositionChanged(self, absolutePosition, private={}):
        self.emit('positionChanged', (absolutePosition, ))

    def getPosition(self):
        return self.position_attr.getValue()

    def move(self, absolutePosition):
        self.position_attr.setValue(absolutePosition)

    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        pass #self._motor_abort()
    
    def light_is_out(self):
        return self.chan_light_is_on.getValue()

    def move_in(self):
        self.chan_light_is_on.setValue(False)

    def move_out(self):
        self.chan_light_is_on.setValue(True)

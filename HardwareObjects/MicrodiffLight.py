from HardwareRepository.BaseHardwareObjects import Device
import math
import logging
import time

class MicrodiffLight(Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

    def __init__(self, name):
        Device.__init__(self, name)
        self.motor_pos_attr_suffix = "Factor"

    def init(self): 
        self.motorState = MicrodiffLight.READY
        self.global_state = "STANDBY"
        self.position_attr = self.addChannel({"type":"exporter", "name":"position" }, self.motor_name+self.motor_pos_attr_suffix)
        self.position_attr.connectSignal("update", self.motorPositionChanged)
        self.setIsReady(True)

    def connectNotify(self, signal):
        if self.position_attr.isConnected():
            if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
            elif signal == 'limitsChanged':
                self.motorLimitsChanged()  
 
    def updateState(self):
        self.setIsReady(True) #self.global_state in ("STANDBY","ALARM") and self.motorState > MicrodiffLight.UNUSABLE)
 
    def getState(self):
        return self.motorState
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        return (0, 2)
 
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
    

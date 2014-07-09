from HardwareRepository.BaseHardwareObjects import Device
import math
import logging
import time
import gevent
import types

class RobodiffMotor(Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self): 
        self.motorState = RobodiffMotor.NOTINITIALIZED
        self.username = self.motor_name
        controller = self.getObjectByRole("controller")
        self.direction = self.getProperty("direction") or 1

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motor = getattr(controller, self.motor_name)
        self.connect(self.motor, "position", self.positionChanged)
        self.connect(self.motor, "state", self.updateState)

    def connectNotify(self, signal):
        if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
        elif signal == 'stateChanged':
                self.updateState()
        elif signal == 'limitsChanged':
                self.motorLimitsChanged()  
 
    def updateState(self, state=None):
        if state is None:
            state = self.motor.state()
        # convert from grob state to Hardware Object motor state
        if state == "MOVING":
            state = RobodiffMotor.MOVING
        elif state == "READY":
            state = RobodiffMotor.READY
        elif state == "ONLIMIT":
            state = RobodiffMotor.ONLIMIT
        else:
            state = RobodiffMotor.UNUSABLE

        self.setIsReady(state > RobodiffMotor.UNUSABLE)

        if self.motorState != state:
            self.motorState = state
            self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        self.updateState()
        return self.motorState
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        return self.motor.limits()

    def positionChanged(self, absolutePosition):
        #print self.name(), absolutePosition
        self.emit('positionChanged', (absolutePosition, ))

    def getPosition(self):
        return self.motor.position()

    def getDialPosition(self):
        return self.getPosition()

    def move(self, position):
        self.updateState("MOVING")
        self.motor.move(self.direction*position, wait=False) 

    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def syncMoveRelative(self, relative_position, timeout=None):
        return self.syncMove(self.getPosition() + relative_position)

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
           self.motor.wait_move()

    def syncMove(self, position, timeout=None):
        self.move(position)
        self.waitEndOfMove(timeout)

    def motorIsMoving(self):
        return self.motorState == RobodiffMotor.MOVING
 
    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        self.motor.stop()

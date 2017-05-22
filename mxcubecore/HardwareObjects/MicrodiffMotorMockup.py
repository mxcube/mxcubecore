import logging
from AbstractMotor import AbstractMotor
from HardwareRepository.BaseHardwareObjects import Device


class MicrodiffMotorMockup(AbstractMotor, Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
    EXPORTER_TO_MOTOR_STATE = { "Invalid": NOTINITIALIZED,
                                "Fault": UNUSABLE,
                                "Ready": READY,
                                "Moving": MOVING,
                                "Created": NOTINITIALIZED,
                                "Initializing": NOTINITIALIZED,
                                "Unknown": UNUSABLE }

    def __init__(self, name):
        AbstractMotor.__init__(self)
        Device.__init__(self, name)

    def init(self): 
        # this is ugly : I added it to make the centring procedure happy
        self.motorState = MicrodiffMotorMockup.READY
        self.motorPosition = 10.124

    def isReady(self):
        return True 

    def connectNotify(self, signal):
        if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
        elif signal == 'stateChanged':
                self.motorStateChanged(self.getState())
        elif signal == 'limitsChanged':
                self.motorLimitsChanged()  
 
    def updateState(self):
        pass

    def updateMotorState(self, motor_states):
        pass

    def motorStateChanged(self, state):
        self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        return self.motorState
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        return (-1E4,1E4)
 
    def getPosition(self):
        return self.motorPosition

    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition):
        self.motorPosition = absolutePosition
        self.emit('positionChanged', (self.motorPosition, ))
        self.emit('stateChanged', (self.motorState, ))

    def moveRelative(self, relativePosition):
        self.motorPosition = self.motorPosition + relativePosition
        self.emit('positionChanged', (self.motorPosition, ))
        self.emit('stateChanged', (self.motorState, ))

    def syncMoveRelative(self, relative_position, timeout=None):
        self.syncMove(self.getPosition() + relative_position)

    def waitEndOfMove(self, timeout=None):
        pass

    def syncMove(self, position, timeout=None):
        self.move(position)

    def motorIsMoving(self):
        return False

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        pass

    def getPredefinedPositionsList(self):
        #For zoom
        return {"Zoom 1": 1, "Zoom 2": 2, "Zoom 3": 3, "Zoom 4": 4, "Zoom 5": 5}

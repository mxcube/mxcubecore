from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.BaseHardwareObjects import Null
from HardwareRepository import HardwareRepository
import math
import logging 
import _tine as tine
from qt import *

(NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

def energyConverter(wavelength):
    energy = float(12.398425/wavelength)
    return energy

class TINEMotor(Device):    
  
    def __init__(self, name): 
        Device.__init__(self, name)	
        """ TINE Motor Class """ 
	self.objName = name  
        self.motorState = READY
        self.motorState2 = 'noninit'
        self.limits = (None, None)
	self.previousPosition = 0.0
	
    def init(self):
        
        self.chanMotorPosition = self.getChannelObject('axisposition')
        self.chanMotorPosition.connectSignal('update', self.motorPositionChanged)

        try:
            self.chanMotorState = self.getChannelObject('axisstate')
            self.chanMotorState.connectSignal('update', self.motorStateChanged)
        except KeyError:
            pass

        try:
            self.chanMotorLimits = self.getChannelObject('axisLimits')
            self.chanMotorLimits.connectSignal('update', self.motorLimitsChanged)
        except KeyError:
            pass

        try:
            self.cmdsetPosition = self.getCommandObject('setPosition')
            self.cmdsetPosition.connectSignal('connected', self.connected)
            self.cmdsetPosition.connectSignal('disconnected', self.disconnected)
        except KeyError:
            pass    
    
        try:
            self.cmdstopAxis = self.getCommandObject('stopAxis')
            self.cmdstopAxis.connectSignal('connected', self.connected)
            self.cmdstopAxis.connectSignal('disconnected', self.disconnected)
        except KeyError:
            pass    

 	self.converter = self.getProperty("converter") 
	self.epsilon = self.getProperty("epsilon")    
	self.verboseUpdate = self.getProperty("verboseUpdate")
        self.maxMotorPosition = self.getProperty("maxMotorPosition")
        self.moveConditions = self.getProperty("moveConditions")
        self.moveHOSignals = self.getProperty("moveHOSignals")

        try:
            hoSignals = eval(self.moveHOSignals)
            for ho in hoSignals:
                hobj = HardwareRepository.HardwareRepository().getHardwareObject("/%s" % ho)
                if hobj is None:
                    logging.getLogger("HWR").error('TINEMotor: invalid %s hardware object' % ho)
                else:
                    exec("self.%s=hobj" % ho)
                    self.connect(eval("self.%s" % ho), PYSIGNAL(hoSignals[ho]), self.getState)
        except:
            pass
             
    def connected(self):
        self.setIsReady(True) 
     
    def disconnected(self):
        self.setIsReady(True)

    def connectNotify(self, signal):
        if self.connected():
            if signal == 'stateChanged':
                self.motorStateChanged()
            elif signal == 'limitsChanged':
                self.motorLimitsChanged(self.getLimits())
            elif signal == 'positionChanged':
                self.motorPositionChanged(self.getPosition())
    
    def motorLimitsChanged(self, limits):
        self.emit('limitsChanged', (limits, ))

    def getLimits(self):
        self.limits = self.chanMotorLimits.getValue()
        return self.limits
  
    def getState(self):

        if (self.moveConditions and not self.checkConditions(self.moveConditions)):
            self.motorState = UNUSABLE
            self.motorState2 = 'unusable'
            self.emit('stateChanged', (self.motorState, ))
            return self.motorState

        actualState = self.chanMotorState.getValue()

        if (actualState != self.motorState2):
            if actualState == 'ready':
                self.motorState = READY
            elif actualState == 'moving':
                self.motorState = MOVING
            self.emit('stateChanged', (self.motorState, ))            
                
        if actualState == 'ready':
            self.motorState2 = actualState
            self.motorState = READY
        elif actualState == 'moving':
            self.motorState2 = actualState
            self.motorState = MOVING
        return self.motorState 
        
       
    #Returns the position
    def getPosition(self):
        value = self.chanMotorPosition.getValue()
	
	if self.converter is not None:
	    value = eval(self.converter)(value)
        return value

    def stop(self):
        self.cmdstopAxis()
    
    def move(self, target):
	self.__changeMotorState(MOVING)
        self.chanMotorState.setOldValue('moving')
        self.cmdsetPosition(target)

    def __changeMotorState(self, state):
        """Private method for changing the SpecMotor object's internal state

        Arguments:
        state -- the motor state
        """
        self.motorState = state
        self.emit('stateChanged', (state, ))
        
    def motorStateChanged(self, dummyState):
        """Callback to take into account a motor state update
        """
        state = self.getState()
        self.emit('stateChanged', (state, ))
        
    def motorPositionChanged(self, dummyArgument):
	position = self.getPosition()
	if ( self.epsilon is None ) or (abs(float(position)-float(self.previousPosition)) > float(self.epsilon) ) : 

	    self.emit('positionChanged', (position,))
	    if (self.verboseUpdate == True ) :
		logging.getLogger().debug('Updating motor postion %s to %s from %s ' %(self.objName,position,self.previousPosition))
            self.previousPosition = position

    def getMotorMnemonic(self):
        return "TINEMotor"

    def getMotorStatus(self, motorName):

        state_message = ""
        state_OK = True

        if self.maxMotorPosition:
            if self.getPosition() > self.maxMotorPosition:
                state_OK = None
                state_message = "%s is possibly out of range.\nDo not recommend to proceed!" % motorName

        return state_OK, state_message
            
    def checkConditions(self, cond_dict):
        conditions = eval(cond_dict)
        for cond in conditions:
            if (conditions[cond] != eval("self.%s" % cond)):
                return False
        return True
    

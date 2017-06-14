# -*- coding: utf-8 -*-
from HardwareRepository.BaseHardwareObjects import Device
import math
# can we get rid of this?
from qt import *
import logging
import time
class MD2TimeoutError:
    pass

class MicrodiffMotorPX2(Device):      

    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

    MotorLimits = {'CentringTableYAxis': (-7., 7.), 'CentringTableXAxis': (-7., 7.), 'Phi': (-360., 360.), 'PhiTableXAxis': (-0.15, 0.15), 'PhiTableYAxis': (-7., 7.), 'PhiTableZAxis': (-7, 7)}

    def __init__(self, name):
        Device.__init__(self, name)
        self.motor_pos_attr_suffix = "Position"
        self.offset = 0
        
    def init(self): 
        self.motorState   = MicrodiffMotorPX2.NOTINITIALIZED
        self.global_state = ""

        logging.info("Initiliazing motor %s on device %s " % (self.name(), self.tangoname) )

        # For some reason addChannel in polling mode does not seem to work with present version
        # to be checked with Matias ?

        #self.position_attr_name = self.motor_name + self.motor_pos_attr_suffix
        #self.position_attr = self.addChannel({"type":"tango", "name":"myposition", "polling":"1000" }, self.position_attr_name )
        #self.state_attr = self.addChannel({"type":"tango", "name":"state", "polling":"1000" }, "State")
        #self.motors_state_attr = self.addChannel({"type":"tango", "name":"motor_states", "polling":"1000"}, "MotorStates")
        #self.motors_state_attr.connectSignal("update", self._motorStateChanged)
        
        self.position_attr = self.getChannelObject("position")
        self.position_attr.connectSignal("update", self.motorPositionChanged)
        
        self.state_attr = self.getChannelObject("state")
        self.state_attr.connectSignal("update", self.globalStateChanged )
        
        logging.info("Position motor %s at init time is %s " % (self.name(), self.position_attr.getValue() ) )

        self._motor_abort = self.addCommand( {"type":"tango", "name":"abort" }, "Reset")

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

    def connectNotify(self, signal):
        if signal == 'positionChanged':
            self.emit('positionChanged', (self.getPosition(), ))
        elif signal == 'stateChanged':
            self.motorStateChanged(self.getState())
        elif signal == 'limitsChanged':
            self.motorLimitsChanged()  
 
    def globalStateChanged(self, state):
        logging.getLogger().debug("motor %s: Global state is %s", self.name(), str(state))
        self.global_state = str(state)
        self.updateState()

    def motorIsMoving(self):
        return (self.global_state == self.MOVING )

    def updateState(self):
        if self.global_state in ("ALARM", ):
            self.motorState = self.UNUSABLE
        elif self.global_state in ("MOVING", ):
            self.motorState = self.MOVING
        elif self.global_state in ("STANDBY", ):
            self.motorState = self.READY
        else:
            self.motorState = self.UNUSABLE

        logging.info("microdiffMotorPX2: motor: %s - global state is %s (motor is %d) " % (self.name(), self.global_state, self.motorState) )

        self.emit('stateChanged', (self.motorState, ))

        self.setIsReady(self.global_state in ("STANDBY","ALARM") and self.motorState > self.UNUSABLE)

    def _motorStateChanged(self, motor_states):
        logging.info("motor states changed")
        d = dict([x.split("=") for x in motor_states.split()])
        new_motor_state = int(d[self.motor_name])
        if self.motorState == new_motor_state:
          return
        self.motorState = new_motor_state
        self.motorStateChanged(self.motorState)

    def motorStateChanged(self, state):
        self.motorState = state
        self.updateState()
        self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        return self.motorState
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        logging.info("Limits for motor %s are %s" % (self.motor_name, self.limits) )
        try:
          #info = self.position_attr.getInfo()
          #return (float(info.min_value)+self.offset, float(info.max_value)+self.offset)
          #MS 29.01.13
          return map(float,self.limits.split())
          return self.MotorLimits[self.motor_name]
        except:
          return (-1., 1.)
 
    def motorPositionChanged(self, absolutePosition, private={}):
        # Commented MS 16.11.2012
        #if math.fabs(absolutePosition - private.get("old_pos", 1E12))<=1E-3:
        #  return 
        #private["old_pos"]=absolutePosition 

        logging.getLogger().debug("%s: position changed %f", self.name(), absolutePosition)
        self.emit('positionChanged', (absolutePosition, ))

    def getPosition(self):
        return self.position_attr.getValue()

    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition):
        self.position_attr.setValue(absolutePosition) #absolutePosition-self.offset)
        
    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def syncMove(self, position, timeout=None):
        self.move(position)
        t0=time.time()  
        s = "MOVING"
        while s=="MOVING":
          s = str(self.state_attr.getValue())
          qApp.processEvents(20)
          if timeout is not None:
              if time.time()-t0 > timeout:
                raise MD2TimeoutError 

    def motorIsMoving(self):
        return self.isReady() and str(self.state_attr.getValue()) == "MOVING"
 

    def syncMoveRelative(self, position, timeout=None):
        #self.moveRelative(position, timeout)
        self.moveRelative(position)

        s = "MOVING"
        while s=="MOVING":
          s = str(self.state_attr.getValue())
          qApp.processEvents(20)
 
    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        self._motor_abort()

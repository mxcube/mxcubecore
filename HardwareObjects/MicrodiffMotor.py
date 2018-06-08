import math
import logging
import time
from gevent import Timeout
from AbstractMotor import AbstractMotor
import traceback

class MD2TimeoutError(Exception):
    pass

"""
Example xml file:
<device class="MicrodiffMotor">
  <username>phiy</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <motor_name>AlignmentY</motor_name>
  <GUIstep>1.0</GUIstep>
  <unit>-1e-3</unit>
  <resolution>1e-2</resolution>
</device>
"""

class MicrodiffMotor(AbstractMotor):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,3,4,5,6)
    EXPORTER_TO_MOTOR_STATE = { "Invalid": NOTINITIALIZED,
                                "Fault": UNUSABLE,
                                "Ready": READY,
                                "Moving": MOVING,
                                "Created": NOTINITIALIZED,
                                "Initializing": NOTINITIALIZED,
                                "Unknown": UNUSABLE,
                                "Offline": UNUSABLE,
                                "LowLim": ONLIMIT,
                                "HighLim": ONLIMIT }

    TANGO_TO_MOTOR_STATE = {"STANDBY": READY,
                            "MOVING": MOVING}
    
    def __init__(self, name):
        AbstractMotor.__init__(self, name) 
        self.motor_pos_attr_suffix = "Position"
        self.motor_state_attr_suffix = "State"
    
    def init(self):
        self.position = None
        #assign value to motor_name
        self.motor_name = self.getProperty("motor_name")
 
        self.GUIstep = self.getProperty("GUIstep")
        
        self.motor_resolution = self.getProperty("resolution")
        if self.motor_resolution is None:
           self.motor_resolution = 0.0001

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motorState = MicrodiffMotor.NOTINITIALIZED
        
        self.position_attr = self.getChannelObject("%s%s" % (self.motor_name, self.motor_pos_attr_suffix))
        self.state_attr = self.getChannelObject("%s%s" % (self.motor_name, self.motor_state_attr_suffix))
        
        if self.position_attr is not None:
            self.position_attr.connectSignal("update", self.motorPositionChanged)
            self.state_attr.connectSignal("update", self.motorStateChanged)
            
            self._motor_abort = self.getCommandObject("abort")
            self.get_dynamic_limits_cmd = self.getCommandObject("get%sDynamicLimits" % self.motor_name)
            self.get_limits_cmd = self.getCommandObject("getMotorLimits")
            self.get_max_speed_cmd = self.getCommandObject("getMotorMaxSpeed")
            self.home_cmd = self.getCommandObject("homing")
            
        self.motorPositionChanged(self.position_attr.getValue())

    def connectNotify(self, signal):
        if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
        elif signal == 'stateChanged':
                self.motorStateChanged(self.getState())
        elif signal == 'limitsChanged':
                self.motorLimitsChanged()  
 
    def updateState(self):
        self.setIsReady(self.motorState > MicrodiffMotor.UNUSABLE)

    def setIsReady(self, value):
        if value == True:
            self.set_ready()
            
    def updateMotorState(self, motor_states):
        d = dict([x.split("=") for x in motor_states])
        #Some are like motors but have no state
        # we set them to ready
        if d.get(self.motor_name) is None:
            new_motor_state = MicrodiffMotor.READY    
        else:
            if d[self.motor_name] in MicrodiffMotor.EXPORTER_TO_MOTOR_STATE:
                new_motor_state = MicrodiffMotor.EXPORTER_TO_MOTOR_STATE[d[self.motor_name]]
            else:
                new_motor_state = MicrodiffMotor.TANGO_TO_MOTOR_STATE[d[self.motor_name]]
        if self.motorState == new_motor_state:
          return
        self.motorState = new_motor_state
        self.motorStateChanged(self.motorState)

    def motorStateChanged(self, state):
        self.getState()
        #if state in MicrodiffMotor.EXPORTER_TO_MOTOR_STATE:
            #self.motorState = MicrodiffMotor.EXPORTER_TO_MOTOR_STATE[state]
        #else:
            #self.motorState = MicrodiffMotor.TANGO_TO_MOTOR_STATE[state.name]
        logging.getLogger().debug("%s: in motorStateChanged: motor state changed to %s", self.name(), state)
        self.updateState()
        self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        if self.motorState == MicrodiffMotor.NOTINITIALIZED:
            if self.state_attr.getValue() in MicrodiffMotor.EXPORTER_TO_MOTOR_STATE:
                self.motorState = MicrodiffMotor.EXPORTER_TO_MOTOR_STATE[self.state_attr.getValue()]
            else:
                self.motorState = MicrodiffMotor.TANGO_TO_MOTOR_STATE[self.state_attr.getValue().name]
            self.motorStateChanged(self.motorState)
                #self.updateMotorState(self.motors_state_attr.getValue())
        return self.motorState
    
    def get_state(self):
        return self.getState()
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        dynamic_limits = self.getDynamicLimits()
        if dynamic_limits != (-1E4, 1E4):
            return dynamic_limits
        else: 
            try:
              low_lim,hi_lim = map(float, self.get_limits_cmd(self.motor_name))
              if low_lim==float(1E999) or hi_lim==float(1E999):
                  raise ValueError
              return low_lim, hi_lim
            except:
              return (-1E4, 1E4)

    def get_limits(self):
        return self.getLimits()
    
    def getDynamicLimits(self):
        try:
          low_lim,hi_lim = map(float, self.get_dynamic_limits_cmd(self.motor_name))
          if low_lim==float(1E999) or hi_lim==float(1E999):
            raise ValueError
          return low_lim, hi_lim
        except:
          return (-1E4, 1E4)

    def getMaxSpeed(self):
        return self.get_max_speed_cmd(self.motor_name)

    def motorPositionChanged(self, absolute_position, private={}):
        if not None in (absolute_position, self.position):
            if abs(absolute_position - self.position) <= self.motor_resolution:
                return
        self.position = absolute_position
        self.emit('positionChanged', (self.position, ))

    def getPosition(self):
        if self.position_attr is not None:   
           self.position = self.position_attr.getValue()
        return self.position
    
    def get_position(self):
        return self.getPosition()
    
    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition, wait=True, timeout=None):
        #if self.getState() != MicrodiffMotor.NOTINITIALIZED:
        if abs(self.position - absolutePosition) >= self.motor_resolution:
           self.position_attr.setValue(absolutePosition) #absolutePosition-self.offset)

    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def syncMoveRelative(self, relative_position, timeout=None):
        return self.syncMove(self.getPosition() + relative_position)

    def waitEndOfMove(self, timeout=None):
        with Timeout(timeout):
           time.sleep(0.1)
           while self.motorState == MicrodiffMotor.MOVING:
              time.sleep(0.1) 

    def syncMove(self, position, timeout=None):
        self.move(position)
        try:
          self.waitEndOfMove(timeout)
        except:
          raise MD2TimeoutError

    def motorIsMoving(self):
        return self.isReady() and self.motorState == MicrodiffMotor.MOVING 
 
    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        if self.getState() != MicrodiffMotor.NOTINITIALIZED:
          self._motor_abort()

    def homeMotor(self, timeout=None):
        self.home_cmd(self.motor_name)
        try:
            self.waitEndOfMove(timeout)
        except:
            raise MD2TimeoutError

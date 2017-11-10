import math
import logging
import time
from gevent import Timeout
from AbstractMotor import AbstractMotor
from HardwareRepository.BaseHardwareObjects import Device

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

class MicrodiffMotor(AbstractMotor, Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
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

    def __init__(self, name):
        AbstractMotor.__init__(self) 
        Device.__init__(self, name)
        self.motor_pos_attr_suffix = "Position"

    def init(self): 
        self.position = None
        #assign value to motor_name
        self.motor_name = self.getProperty("motor_name")
 
        self.motor_resolution = self.getProperty("resolution")
        if self.motor_resolution is None:
           self.motor_resolution = 0.0001

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motorState = MicrodiffMotor.NOTINITIALIZED

        self.position_attr = self.addChannel({"type": "exporter", 
                                              "name": "%sPosition" %self.motor_name}, 
                                               self.motor_name + self.motor_pos_attr_suffix)
        if self.position_attr is not None:
          self.position_attr.connectSignal("update", self.motorPositionChanged)
          self.state_attr = self.addChannel({"type":"exporter", "name":"state" }, "State")
          #self.state_attr.connectSignal("update", self.globalStateChanged)
          self.motors_state_attr = self.addChannel({"type":"exporter", "name":"motor_states"}, "MotorStates")
          self.motors_state_attr.connectSignal("update", self.updateMotorState)
          self._motor_abort = self.addCommand( {"type":"exporter", "name":"abort" }, "abort")
          self.get_dynamic_limits_cmd = self.addCommand({"type": "exporter",
                                                         "name": "get%sDynamicLimits" % self.motor_name},
                                                         "getMotorDynamicLimits")
          self.get_limits_cmd = self.addCommand( { "type": "exporter", "name": "get_limits"}, "getMotorLimits")
          self.get_max_speed_cmd = self.addCommand( { "type": "exporter", "name": "get_max_speed"}, "getMotorMaxSpeed")
          self.home_cmd = self.addCommand( {"type":"exporter", "name":"homing" }, "startHomingMotor")

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

    def updateMotorState(self, motor_states):
        d = dict([x.split("=") for x in motor_states])
        #Some are like motors but have no state
        # we set them to ready
        if d.get(self.motor_name) is None:
            new_motor_state = MicrodiffMotor.READY    
        else:
            new_motor_state = MicrodiffMotor.EXPORTER_TO_MOTOR_STATE[d[self.motor_name]]
        if self.motorState == new_motor_state:
          return
        self.motorState = new_motor_state
        self.motorStateChanged(self.motorState)

    def motorStateChanged(self, state):
        #logging.getLogger().debug("%s: in motorStateChanged: motor state changed to %s", self.name(), state)
        self.updateState()
        self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        if self.motorState == MicrodiffMotor.NOTINITIALIZED:
          try:
            self.updateMotorState(self.motors_state_attr.getValue())
          except:
            return MicrodiffMotor.NOTINITIALIZED
        return self.motorState
    
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
        #if self.getState() != MicrodiffMotor.NOTINITIALIZED:
        #  print "MicrodiffMotor.NOTINITIALIZED:"
        #if self.position_attr is not None:   
        #    self.position = self.position_attr.getValue()
        return self.position

    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition):
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

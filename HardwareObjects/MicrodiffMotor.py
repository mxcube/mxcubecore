from HardwareRepository.BaseHardwareObjects import Device
import math
import logging
import time
import gevent

class MD2TimeoutError(Exception):
    pass

"""
Exaplle xml file:
<device class="MicrodiffMotor">
  <username>phiy</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <motor_name>AlignmentY</motor_name>
  <GUIstep>1.0</GUIstep>
  <unit>-1e-3</unit>
</device>
"""

class MicrodiffMotor(Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
    EXPORTER_TO_MOTOR_STATE = { "Invalid": NOTINITIALIZED,
                                "Fault": UNUSABLE,
                                "Ready": READY,
                                "Moving": MOVING,
                                "Created": NOTINITIALIZED,
                                "Initializing": NOTINITIALIZED,
                                "Unknown": UNUSABLE,
                                "LowLim": ONLIMIT,
                                "HighLim": ONLIMIT }

    def __init__(self, name):
        Device.__init__(self, name)
        self.motor_pos_attr_suffix = "Position"

    def init(self): 
        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motorState = MicrodiffMotor.NOTINITIALIZED

        self.position_attr = self.addChannel({"type":"exporter", "name":"position"  }, self.motor_name+self.motor_pos_attr_suffix)
        if self.position_attr is not None:
          self.position_attr.connectSignal("update", self.motorPositionChanged)
          self.state_attr = self.addChannel({"type":"exporter", "name":"state" }, "State")
          #self.state_attr.connectSignal("update", self.globalStateChanged)
          self.motors_state_attr = self.addChannel({"type":"exporter", "name":"motor_states"}, "MotorStates")
          self.motors_state_attr.connectSignal("update", self.updateMotorState)
          self._motor_abort = self.addCommand( {"type":"exporter", "name":"abort" }, "abort")
          #TODO: dynamic limits
          #self.motor_limits_attr = self.addChannel({"type":"exporter", "name":"limits"}, self.motor_name+"DynamicLimits" )
          self.get_limits_cmd = self.addCommand( { "type": "exporter", "name": "get_limits"}, "getMotorLimits")
          self.home_cmd = self.addCommand( {"type":"exporter", "name":"homing" }, "startHomingMotor")

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
        new_motor_state = MicrodiffMotor.EXPORTER_TO_MOTOR_STATE[d[self.motor_name]]
        if self.motorState == new_motor_state:
          return
        self.motorState = new_motor_state
        self.motorStateChanged(self.motorState)

    def motorStateChanged(self, state):
        logging.getLogger().debug("%s: in motorStateChanged: motor state changed to %s", self.name(), state)
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
        return (-1E4,1E4)
        try:
          low_lim,hi_lim = map(float, self.get_limits_cmd(self.motor_name))
          if low_lim==float(1E999) or hi_lim==float(1E999):
            raise ValueError
          return low_lim, hi_lim
        except:
          return (-1E4, 1E4)
 
    def motorPositionChanged(self, absolutePosition, private={}):
        if math.fabs(absolutePosition - private.get("old_pos", 1E12))<=1E-3:
          return 
        private["old_pos"]=absolutePosition 

        self.emit('positionChanged', (absolutePosition, ))

    def getPosition(self):
        if self.getState() != MicrodiffMotor.NOTINITIALIZED:
          return self.position_attr.getValue()

    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition):
        if self.getState() != MicrodiffMotor.NOTINITIALIZED:
          self.position_attr.setValue(absolutePosition) #absolutePosition-self.offset)
          self.motorStateChanged(MicrodiffMotor.MOVING)

    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def syncMoveRelative(self, relative_position, timeout=None):
        return self.syncMove(self.getPosition() + relative_position)

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
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

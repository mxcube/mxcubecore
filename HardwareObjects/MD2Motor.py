import logging
import time
from gevent import Timeout
from AbstractMotor import AbstractMotor
from HardwareRepository.BaseHardwareObjects import Device

class MD2TimeoutError(Exception):
    pass

class MD2Motor(AbstractMotor, Device):

    def __init__(self, name):
        AbstractMotor.__init__(self)
        Device.__init__(self, name)

        self.motor_pos_attr_suffix = "Position"

    def init(self):
        self.motorState = MD2Motor.NOTINITIALIZED
        if self.motor_name is None:
            self.motor_name = self.getProperty("motor_name")

        self.motor_resolution = self.getProperty("resolution")
        if self.motor_resolution is None:
            self.motor_resolution = 1E-3

        self.position_attr = self.addChannel({"type":"exporter",
                                              "name":"position" },
                                             self.motor_name+self.motor_pos_attr_suffix)
        if self.position_attr is not None:
          self.position_attr.connectSignal("update", self.motorPositionChanged)

          self.state_attr = self.addChannel({"type":"exporter",
                                             "name":"%sState" %  self.motor_name},
                                            "State")

          self.motors_state_attr = self.addChannel({"type":"exporter",
                                                    "name":"MotorStates"}, "MotorStates")
          if self.motors_state_attr is not None:
              self.motors_state_attr.connectSignal("update", self.updateMotorState)

          self._motor_abort = self.addCommand( {"type":"exporter", "name":"abort" },
                                               "abort")
      
          self.get_limits_cmd = self.addCommand({ "type": "exporter",
                                                  "name": "get%sLimits" % self.motor_name},
                                                "getMotorLimits")
          self.get_dynamic_limits_cmd = self.addCommand({"type": "exporter",
                                                         "name": "get%sDynamicLimits" % self.motor_name},
                                                        "getMotorDynamicLimits")

          self.home_cmd = self.addCommand( {"type":"exporter", "name":"%sHoming" % self.motor_name},
                                           "startHomingMotor")

    def connectNotify(self, signal):
        if signal == 'positionChanged':
                self.emit('positionChanged', (self.getPosition(), ))
        elif signal == 'stateChanged':
                self.motorStateChanged(self.getState())
        elif signal == 'limitsChanged':
                self.motorLimitsChanged()

    def updateState(self):
        self.setIsReady(self.motorState > MD2Motor.UNUSABLE)

    def updateMotorState(self, motor_states):
        d = dict([x.split("=") for x in motor_states])
        new_motor_state = MD2Motor.EXPORTER_TO_MOTOR_STATE[d[self.motor_name]]
        if self.motorState == new_motor_state:
          return
        self.motorState = new_motor_state
        self.motorStateChanged(self.motorState)

    def motorStateChanged(self, state):
        logging.getLogger().debug("%s: in motorStateChanged: motor state changed to %s", self.name(), state)
        self.updateState()
        self.emit('stateChanged', (self.motorState, ))

    def getState(self):
        if self.motorState == MD2Motor.NOTINITIALIZED:
          try:
            self.updateMotorState(self.motors_state_attr.getValue())
          except:
            return MD2Motor.NOTINITIALIZED
        return self.motorState

    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))

    def getDynamicLimits(self):
        try:
            low_lim,hi_lim = map(float, self.get_dynamic_limits_cmd(self.motor_name))
            if low_lim==float(1E999) or hi_lim==float(1E999):
                raise ValueError
            return low_lim, hi_lim
        except:
            return (-1E4, 1E4)

    def getLimits(self):
        try:
            low_lim,hi_lim = map(float, self.get_limits_cmd(self.motor_name))
            if low_lim==float(1E999) or hi_lim==float(1E999):
                raise ValueError
            return low_lim, hi_lim
        except:
            return (-1E4, 1E4)

    def motorPositionChanged(self, absolutePosition, private={}):
        if abs(absolutePosition - private.get("old_pos", 1E12))<=self.motor_resolution:
            return
        private["old_pos"]=absolutePosition

        self.emit('positionChanged', (absolutePosition, ))

    def getPosition(self):
        if self.getState() != MD2Motor.NOTINITIALIZED:
            return self.position_attr.getValue()

    def getDialPosition(self):
        return self.getPosition()

    def move(self, absolutePosition, timeout=None, wait=False):
        if self.getState() != MD2Motor.NOTINITIALIZED:
          self.position_attr.setValue(absolutePosition)
          self.motorStateChanged(MD2Motor.MOVING)
        if wait:
            try:
                self.waitEndOfMove(timeout)
            except:
                raise MD2TimeoutError

    def moveRelative(self, relativePosition, wait=False, timeout=None):
        self.move(self.getPosition() + relativePosition)
        if wait:
            try:
                self.waitEndOfMove(timeout)
            except:
                raise MD2TimeoutError

    def waitEndOfMove(self, timeout=None):
        with Timeout(timeout):
           time.sleep(0.1)
           while self.motorState == MD2Motor.MOVING:
              time.sleep(0.1)

    def motorIsMoving(self):
        return self.isReady() and self.motorState == MD2Motor.MOVING

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        if self.getState() != MD2Motor.NOTINITIALIZED:
          self._motor_abort()

    def homeMotor(self, timeout=None):
        self.home_cmd(self.motor_name)
        try:
            self.waitEndOfMove(timeout)
        except:
            raise MD2TimeoutError

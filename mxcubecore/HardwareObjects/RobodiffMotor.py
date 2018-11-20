from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository import HardwareRepository
import math
import logging
import time
import gevent
import types


class RobodiffMotor(Device):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        Device.__init__(self, name)
        self.__initialized = False

    def init(self):
        self.motorState = RobodiffMotor.NOTINITIALIZED
        self.username = self.motor_name
        # gevent.spawn_later(1, self.end_init)

    def end_init(self):
        if self.__initialized:
            return
        controller = HardwareRepository.HardwareRepository().getHardwareObject(
            self.getProperty("controller")
        )  # self.getObjectByRole("controller")

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motor = getattr(controller, self.motor_name)
        self.connect(self.motor, "position", self.positionChanged)
        self.connect(self.motor, "state", self.updateState)
        self.__initialized = True

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.emit("positionChanged", (self.getPosition(),))
        elif signal == "stateChanged":
            self.updateState(emit=True)
        elif signal == "limitsChanged":
            self.motorLimitsChanged()

    def updateState(self, state=None, emit=False):
        self.end_init()
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
            emit = True
        if emit:
            self.emit("stateChanged", (self.motorState,))

    def getState(self):
        self.end_init()
        self.updateState()
        return self.motorState

    def motorLimitsChanged(self):
        self.end_init()
        self.emit("limitsChanged", (self.getLimits(),))

    def getLimits(self):
        self.end_init()
        return self.motor.limits()

    def positionChanged(self, absolutePosition):
        # print self.name(), absolutePosition
        self.emit("positionChanged", (absolutePosition,))

    def getPosition(self):
        self.end_init()
        return self.motor.position()

    def getDialPosition(self):
        self.end_init()
        return self.getPosition()

    def move(self, position):
        self.end_init()
        self.updateState("MOVING")
        self.motor.move(position, wait=False)

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
        self.end_init()
        return self.motorState == RobodiffMotor.MOVING

    def getMotorMnemonic(self):
        self.end_init()
        return self.motor_name

    def stop(self):
        self.end_init()
        self.motor.stop()

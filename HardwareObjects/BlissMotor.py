from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import *
import math
import logging
import time
import gevent
import types
from bliss.config import static
import os


class BlissMotor(Device):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        self.motorState = BlissMotor.NOTINITIALIZED
        self.username = self.motor_name

        cfg = static.get_config()
        self.motor = cfg.get(self.motor_name)
        self.connect(self.motor, "position", self.positionChanged)
        self.connect(self.motor, "state", self.updateState)
        self.connect(self.motor, "move_done", self._move_done)

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.emit("positionChanged", (self.getPosition(),))
        elif signal == "stateChanged":
            self.updateState()
        elif signal == "limitsChanged":
            self.motorLimitsChanged()

    def _move_done(self, move_done):
        if move_done:
            self.updateState("READY")
        else:
            self.updateState("MOVING")

    def updateState(self, state=None):
        if state is None:
            state = self.motor.state()
        # convert from grob state to Hardware Object motor state
        if state == "MOVING":
            state = BlissMotor.MOVING
        elif state == "READY":
            state = BlissMotor.READY
        elif state == "LIMPOS" or state == "LIMNEG":
            state = BlissMotor.ONLIMIT
        else:
            state = BlissMotor.UNUSABLE

        self.setIsReady(state > BlissMotor.UNUSABLE)

        if self.motorState != state:
            self.motorState = state
            self.emit("stateChanged", (self.motorState,))

    def getState(self):
        self.updateState()
        return self.motorState

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.getLimits(),))

    def getLimits(self):
        # no limit = None, but None is a problematic value
        # for some GUI components (like MotorSpinBox), so
        # in case of None it is much easier to return very
        # large limits
        ll, hl = self.motor.limits()
        return ll if ll is not None else -1e6, hl if hl is not None else 1e6

    def positionChanged(self, absolutePosition):
        # print self.name(), absolutePosition
        self.emit("positionChanged", (absolutePosition,))

    def getPosition(self):
        return self.motor.position()

    def getDialPosition(self):
        return self.getPosition()

    """@task
    def _wait_ready(self):
        while self.motorIsMoving():
            time.sleep(0.02)
    """

    def move(self, position):
        # self._wait_ready(timeout=15)
        self.motor.move(position, wait=False)  # .link(self.updateState)

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
        return self.motorState == BlissMotor.MOVING

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        self.motor.stop(wait=False)

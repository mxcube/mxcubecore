from HardwareRepository.BaseHardwareObjects import Device
from SpecClient_gevent.SpecMotor import SpecMotorA


class SpecMotor(Device, SpecMotorA):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        Device.__init__(self, name)
        SpecMotorA.__init__(self)

    def _init(self):
        SpecMotorA.connectToSpec(self, self.specname, self.specversion)

    def connectNotify(self, signal):
        if self.connection.isSpecConnected():
            if signal == "stateChanged":
                self.motorStateChanged(self.getState())
            elif signal == "limitsChanged":
                self.motorLimitsChanged()
            elif signal == "valueChanged":
                self.motorPositionChanged(self.get_value())

    def motorStateChanged(self, state):
        self.setIsReady(state > SpecMotor.UNUSABLE)

        self.emit("stateChanged", (state,))

    def motorIsMoving(self):
        return not self._ready_state_event.is_set()
        # return self.getState() in (SpecMotor.MOVESTARTED, SpecMotor.MOVING)

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.getLimits(),))

    def motorMoveDone(self, channelValue):
        SpecMotorA.motorMoveDone(self, channelValue)

        # print "motor state is ready ? %s (%s)" %
        # ((self.getState()==SpecMotor.READY), self.getState())
        if self.getState() == SpecMotor.READY:
            self.emit("moveDone", (self.specversion, self.specname))

    def motorPositionChanged(self, absolutePosition):
        self.emit("valueChanged", (absolutePosition,))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        pass  # return '0' #NO ('1' means YES)

    def syncMove(self, position, timeout=None):
        # timeout in seconds
        self.move(position, wait=True, timeout=timeout)

    def syncMoveRelative(self, position, timeout=None):
        abs_pos = position + self.get_value()
        return self.syncMove(abs_pos, timeout)

    def getMotorMnemonic(self):
        return self.specName


class SpecVersionMotor(SpecMotor):
    def __init__(self, specversion, specname, username):
        Device.__init__(self, specname)
        self.specversion = specversion
        self.specname = specname
        self.username = username
        SpecMotor.__init__(self, "internal" + username)
        self._init()

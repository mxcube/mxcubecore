from mxcubecore.BaseHardwareObjects import HardwareObject
from SpecClient_gevent.SpecMotor import SpecMotorA


class SpecMotor(HardwareObject, SpecMotorA):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        super().__init__(name)
        SpecMotorA.__init__(self)

    def _init(self):
        SpecMotorA.connectToSpec(self, self.specname, self.specversion)

    def connect_notify(self, signal):
        if self.connection.isSpecConnected():
            if signal == "stateChanged":
                self.motorStateChanged(self.get_state())
            elif signal == "limitsChanged":
                self.motorLimitsChanged()
            elif signal == "valueChanged":
                self.motor_positions_changed(self.get_value())

    def motorStateChanged(self, state):
        self.set_is_ready(state > SpecMotor.UNUSABLE)

        self.emit("stateChanged", (state,))

    def motorIsMoving(self):
        return not self._ready_state_event.is_set()
        # return self.get_state() in (SpecMotor.MOVESTARTED, SpecMotor.MOVING)

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def motorMoveDone(self, channelValue):
        SpecMotorA.motorMoveDone(self, channelValue)

        # print "motor state is ready ? %s (%s)" %
        # ((self.get_state()==SpecMotor.READY), self.get_state())
        if self.get_state() == SpecMotor.READY:
            self.emit("moveDone", (self.specversion, self.specname))

    def motor_positions_changed(self, absolutePosition):
        self.emit("valueChanged", (absolutePosition,))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        pass  # return '0' #NO ('1' means YES)

    def get_motor_mnemonic(self):
        return self.specName


class SpecVersionMotor(SpecMotor):
    def __init__(self, specversion, specname, username):
        super().__init__(specname)
        self.specversion = specversion
        self.specname = specname
        self.username = username
        SpecMotor.__init__(self, "internal" + username)
        self._init()

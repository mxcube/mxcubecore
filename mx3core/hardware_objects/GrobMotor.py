from mx3core.BaseHardwareObjects import Device
from mx3core.hardware_objects.abstract.AbstractMotor import AbstractMotor
import math
import gevent


class GrobMotor(Device, AbstractMotor):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        self.motorState = GrobMotor.NOTINITIALIZED
        self.username = self.motor_name
        self.grob = self.get_object_by_role("grob")

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.motor_name

        self.motor = getattr(self.grob.controller, self.motor_name)
        self.connect(self.motor, "position", self.positionChanged)
        self.connect(self.motor, "state", self.updateState)

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.emit("valueChanged", (self.get_value(),))
        elif signal == "stateChanged":
            self.updateState()
        elif signal == "limitsChanged":
            self.motorLimitsChanged()

    def updateState(self, state=None):
        if state is None:
            state = self.motor.state()
            if isinstance(self.motor, self.grob.SampleTableMotor):
                if self.motor.is_unusable():
                    state = "UNUSABLE"
                elif self.motor.is_moving(state):
                    state = "MOVING"
                elif self.motor.is_on_limit(state):
                    state = "ONLIMIT"
                else:
                    state = "READY"
        # convert from grob state to Hardware Object motor state
        if state == "MOVING":
            state = GrobMotor.MOVING
        elif state == "READY" or state.startswith("WAIT_GET"):
            state = GrobMotor.READY
        elif state == "ONLIMIT":
            state = GrobMotor.ONLIMIT
        else:
            state = GrobMotor.UNUSABLE

        self.set_is_ready(state > GrobMotor.UNUSABLE)

        if self.motorState != state:
            self.motorState = state
            self.emit("stateChanged", (self.motorState,))

    def get_state(self):
        self.updateState()
        return self.motorState

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def get_limits(self):
        return self.motor.get_limits()

    def positionChanged(self, absolutePosition, private={}):
        if math.fabs(absolutePosition - private.get("old_pos", 1e12)) <= 1e-3:
            return
        private["old_pos"] = absolutePosition

        self.emit("valueChanged", (absolutePosition,))

    def get_value(self):
        return self.motor.read_dial()

    def _set_value(self, value):
        if isinstance(self.motor, self.grob.SampleMotor):
            # position has to be relative
            self.motor.set_value_relative(value - self.get_value())
        else:
            self.motor.start_one(value)

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
            self.motor.wait_for_move()

    def motorIsMoving(self):
        return self.is_ready() and self.motor.is_moving()

    def get_motor_mnemonic(self):
        return self.motor_name

    def stop(self):
        pass

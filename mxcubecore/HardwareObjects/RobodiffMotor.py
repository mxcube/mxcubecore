from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR
import gevent


class RobodiffMotor(HardwareObject):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        super().__init__(name)
        self.__initialized = False

    def init(self):
        self.motorState = RobodiffMotor.NOTINITIALIZED
        self.username = self.actuator_name
        # gevent.spawn_later(1, self.end_init)

    def end_init(self):
        if self.__initialized:
            return
        controller = HWR.get_hardware_repository().get_hardware_object(
            self.get_property("controller")
        )  # self.get_object_by_role("controller")

        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.actuator_name

        self.motor = getattr(controller, self.actuator_name)
        self.connect(self.motor, "position", self.positionChanged)
        self.connect(self.motor, "state", self.updateState)
        self.__initialized = True

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.emit("valueChanged", (self.get_value(),))
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

        self.set_is_ready(state > RobodiffMotor.UNUSABLE)

        if self.motorState != state:
            self.motorState = state
            emit = True
        if emit:
            self.emit("stateChanged", (self.motorState,))

    def get_state(self):
        self.end_init()
        self.updateState()
        return self.motorState

    def motorLimitsChanged(self):
        self.end_init()
        self.emit("limitsChanged", (self.get_limits(),))

    def get_limits(self):
        self.end_init()
        return self.motor.limits()

    def positionChanged(self, absolutePosition):
        # print self.name(), absolutePosition
        self.emit("valueChanged", (absolutePosition,))

    def get_value(self):
        self.end_init()
        return self.motor.position()

    def _set_value(self, value):
        self.end_init()
        self.updateState("MOVING")
        self.motor.move(value, wait=False)

    def waitEndOfMove(self, timeout=None):
        with gevent.Timeout(timeout):
            self.motor.wait_move()

    def motorIsMoving(self):
        self.end_init()
        return self.motorState == RobodiffMotor.MOVING

    def get_motor_mnemonic(self):
        self.end_init()
        return self.actuator_name

    def stop(self):
        self.end_init()
        self.motor.stop()

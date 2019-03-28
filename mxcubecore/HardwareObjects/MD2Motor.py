import logging
from gevent import Timeout, sleep
from warnings import warn
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor


class MD2TimeoutError(Exception):
    pass


class MD2Motor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.motor_pos_attr_suffix = "Position"

    def init(self):
        self.motor_state = MD2Motor.NOTINITIALIZED
        if self.motor_name is None:
            self.motor_name = self.getProperty("motor_name")

        self.motor_resolution = self.getProperty("resolution")
        if self.motor_resolution is None:
            self.motor_resolution = 1e-3

        self.position_attr = self.add_channel(
            {"type": "exporter", "name": "position"},
            self.motor_name + self.motor_pos_attr_suffix,
        )
        if self.position_attr is not None:
            self.position_attr.connectSignal("update", self.motorPositionChanged)

            self.state_attr = self.add_channel(
                {"type": "exporter", "name": "%sState" % self.motor_name}, "State"
            )

            self.motors_state_attr = self.add_channel(
                {"type": "exporter", "name": "MotorStates"}, "MotorStates"
            )
            if self.motors_state_attr is not None:
                self.motors_state_attr.connectSignal("update", self.updateMotorState)

            self._motor_abort = self.add_command(
                {"type": "exporter", "name": "abort"}, "abort"
            )

            self.get_limits_cmd = self.add_command(
                {"type": "exporter", "name": "get%sLimits" % self.motor_name},
                "getMotorLimits",
            )
            self.get_dynamic_limits_cmd = self.add_command(
                {"type": "exporter", "name": "get%sDynamicLimits" % self.motor_name},
                "getMotorDynamicLimits",
            )

            self.home_cmd = self.add_command(
                {"type": "exporter", "name": "%sHoming" % self.motor_name},
                "startHomingMotor",
            )

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.emit("positionChanged", (self.get_position(),))
        elif signal == "stateChanged":
            self.updateMotorState(self.motors_state_attr.get_value())
        elif signal == "limitsChanged":
            self.motorLimitsChanged()

    def updateState(self):
        self.setIsReady(self.motor_state > MD2Motor.UNUSABLE)

    def updateMotorState(self, motor_states):
        d = dict([x.split("=") for x in motor_states])
        new_motor_state = MD2Motor.EXPORTER_TO_MOTOR_STATE[d[self.motor_name]]
        if self.motor_state == new_motor_state:
            return
        self.motor_state = new_motor_state
        self.updateState()
        self.motorStateChanged(new_motor_state)

    def motorStateChanged(self, state):
        logging.getLogger().debug(
            "%s: in motorStateChanged: motor state changed to %s", self.name(), state
        )
        self.emit("stateChanged", (state,))

    def motorPositionChanged(self, absolutePosition, private={}):
        if (
            abs(absolutePosition - private.get("old_pos", 1e12))
            <= self.motor_resolution
        ):
            return
        private["old_pos"] = absolutePosition

        self.emit("positionChanged", (absolutePosition,))

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.getLimits(),))

    def get_state(self):
        return self.motor_state

    def get_dynamic_limits(self):
        try:
            low_lim, hi_lim = map(float, self.get_dynamic_limits_cmd(self.motor_name))
            if low_lim == float(1e999) or hi_lim == float(1e999):
                raise ValueError
            return low_lim, hi_lim
        except BaseException:
            return (-1e4, 1e4)

    def get_limits(self):
        try:
            low_lim, hi_lim = map(float, self.get_limits_cmd(self.motor_name))
            if low_lim == float(1e999) or hi_lim == float(1e999):
                raise ValueError
            return low_lim, hi_lim
        except BaseException:
            return (-1e4, 1e4)

    def get_position(self):
        ret = self.position_attr.get_value()
        if ret is None:
            raise RuntimeError("%s: motor position is None" % self.name())
        return ret

    def move(self, position, wait=False, timeout=None):
        self.position_attr.set_value(position)
        self.motorStateChanged(MD2Motor.MOVING)

        if wait:
            try:
                self.waitEndOfMove(timeout)
            except BaseException:
                raise MD2TimeoutError

    def waitEndOfMove(self, timeout=None):
        with Timeout(timeout):
            sleep(0.1)
            while self.motor_state == MD2Motor.MOVING:
                sleep(0.1)

    def motorIsMoving(self):
        return self.isReady() and self.motor_state == MD2Motor.MOVING

    def getMotorMnemonic(self):
        return self.motor_name

    def stop(self):
        if self.getState() != MD2Motor.NOTINITIALIZED:
            self._motor_abort()

    def home_motor(self, timeout=None):
        self.home_cmd(self.motor_name)
        try:
            self.waitEndOfMove(timeout)
        except BaseException:
            raise MD2TimeoutError

    """ obsolete, keep for backward compatibility """

    def getDynamicLimits(self):
        warn(
            "getDynamicLimits is deprecated. Use get_dynamic_limits instead",
            DeprecationWarning,
        )
        return self.get_dynamic_limits()

    def getDialPosition(self):
        warn(
            "getDialPosition is deprecated. Use get_position instead",
            DeprecationWarning,
        )
        return self.get_position()

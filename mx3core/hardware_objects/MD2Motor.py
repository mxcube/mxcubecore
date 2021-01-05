import logging
from gevent import Timeout, sleep
from warnings import warn
from mx3core.hardware_objects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)


class MD2TimeoutError(Exception):
    pass


class MD2Motor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.motor_pos_attr_suffix = "Position"

    def init(self):
        self.motor_state = MotorStates.UNKNOWN
        if self.actuator_name in [None, ""]:
            self.actuator_name = self.get_property("actuator_name")

        self.motor_resolution = self.get_property("resolution")
        if self.motor_resolution is None:
            self.motor_resolution = 1e-3

        self.position_attr = self.add_channel(
            {"type": "exporter", "name": "position"},
            self.actuator_name + self.motor_pos_attr_suffix,
        )

        if self.position_attr is not None:
            self.position_attr.connect_signal("update", self.update_value)

            self.state_attr = self.add_channel(
                {"type": "exporter", "name": "%sState" % self.actuator_name}, "State"
            )

            self.motors_state_attr = self.add_channel(
                {"type": "exporter", "name": "MotorStates"}, "MotorStates"
            )
            if self.motors_state_attr is not None:
                self.motors_state_attr.connect_signal("update", self.updateMotorState)

            self._motor_abort = self.add_command(
                {"type": "exporter", "name": "abort"}, "abort"
            )

            self.get_limits_cmd = self.add_command(
                {"type": "exporter", "name": "get%sLimits" % self.actuator_name},
                "getMotorLimits",
            )
            self.get_dynamic_limits_cmd = self.add_command(
                {"type": "exporter", "name": "get%sDynamicLimits" % self.actuator_name},
                "getMotorDynamicLimits",
            )

            self.home_cmd = self.add_command(
                {"type": "exporter", "name": "%sHoming" % self.actuator_name},
                "startHomingMotor",
            )

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.emit("valueChanged", (self.get_value(),))
        elif signal == "stateChanged":
            self.updateMotorState(self.motors_state_attr.get_value())
        elif signal == "limitsChanged":
            self.motorLimitsChanged()

    def updateMotorState(self, motor_states):
        d = dict([x.split("=") for x in motor_states])

        # new_motor_state = MotorStates.DESC_TO_STATE[d[self.actuator_name]]
        new_motor_state = MotorStates.__members__[d[self.actuator_name].upper()]

        if self.motor_state == new_motor_state:
            return

        self.motor_state = new_motor_state
        self.updateState()
        self.motorStateChanged(new_motor_state)

    def motorStateChanged(self, state):
        logging.getLogger().debug(
            "{}: in motorStateChanged: motor state changed to {}".format(
                self.name(), state
            )
        )
        self.emit("stateChanged", (state,))

    # Replaced by AbstractMotor.update_value:
    #
    # NB - was already broken (__position not set)
    #
    # def motor_positions_changed(self, position, private={}):
    #     """
    #     logging.getLogger().debug(
    #         "{}: in motor_positions_changed: motor position changed to {}".format(self.name(), position))
    #     """
    #     if abs(position - self.__position) <= self.motor_resolution:
    #         return
    #     self.__position = position
    #     print("%s --- %s" % (position, self.__position))
    #     self.emit("valueChanged", (self.__position,))

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def get_state(self):
        return self.motor_state

    def get_dynamic_limits(self):
        try:
            low_lim, hi_lim = map(
                float, self.get_dynamic_limits_cmd(self.actuator_name)
            )
            if low_lim == float(1e999) or hi_lim == float(1e999):
                raise ValueError
            return low_lim, hi_lim
        except Exception:
            return (-1e4, 1e4)

    def get_limits(self):
        try:
            low_lim, hi_lim = map(float, self.get_limits_cmd(self.actuator_name))
            if low_lim == float(1e999) or hi_lim == float(1e999):
                raise ValueError
            return low_lim, hi_lim
        except Exception:
            return (-1e4, 1e4)

    def get_value(self):
        ret = self.position_attr.get_value()
        if ret is None:
            raise RuntimeError("%s: motor position is None" % self.name())
        return ret

    def _set_value(self, value):
        self.position_attr.set_value(value)

    def waitEndOfMove(self, timeout=None):
        self.wait_end_of_move(timeout)

    def wait_end_of_move(self, timeout=None):
        with Timeout(timeout):
            sleep(0.1)
            while self.motor_state == MotorStates.MOVING:
                sleep(0.1)

    def motorIsMoving(self):
        warn("motorIsMoving is deprecated. Use is_ready instead", DeprecationWarning)
        return self.is_ready() and self.motor_state == MotorStates.MOVING

    def get_motor_mnemonic(self):
        return self.actuator_name

    def stop(self):
        if self.get_state() != MotorStates.NOTINITIALIZED:
            self._motor_abort()

    def home_motor(self, timeout=None):
        self.home_cmd(self.actuator_name)
        try:
            self.waitEndOfMove(timeout)
        except Exception:
            raise MD2TimeoutError

import logging
import time
from mx3core.hardware_objects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)
from gevent import Timeout

"""
Interfaces Sardana Motor objects.
taurusname is the only obligatory property.
<device class="SardanaMotor">
    <taurusname>dmot01</taurusname>
    <username>Dummy</username>
    <actuator_name>dummy_motor</actuator_name>
    <threshold>0.005</threshold>
    <move_threshold>0.005</move_threshold>
    <interval>2000</interval>
</device>
"""


class SardanaMotor(AbstractMotor):

    suffix_position = "Position"
    suffix_state = "State"
    suffix_stop = "Stop"
    suffix_velocity = "Velocity"
    suffix_acceleration = "Acceleration"

    state_map = {
        "ON": MotorStates.READY,
        "OFF": MotorStates.OFF,
        "CLOSE": MotorStates.DISABLED,
        "OPEN": MotorStates.DISABLED,
        "INSERT": MotorStates.DISABLED,
        "EXTRACT": MotorStates.DISABLED,
        "MOVING": MotorStates.MOVING,
        "STANDBY": MotorStates.READY,
        "FAULT": MotorStates.FAULT,
        "INIT": MotorStates.INITIALIZING,
        "RUNNING": MotorStates.MOVING,
        "ALARM": MotorStates.ALARM,
        "DISABLE": MotorStates.DISABLED,
        "UNKNOWN": MotorStates.UNKNOWN,
    }

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.stop_command = None
        self.position_channel = None
        self.state_channel = None
        self.taurusname = None
        self.motor_position = 0.0
        self.threshold_default = 0.0018
        self.move_threshold_default = 0.0
        self.polling_default = "events"
        self.limit_upper = None
        self.limit_lower = None
        self.static_limits = (-1e4, 1e4)
        self.limits = (None, None)
        self.motor_state = MotorStates.NOTINITIALIZED

    def init(self):

        self.taurusname = self.get_property("taurusname")
        if not self.taurusname:
            raise RuntimeError("Undefined property taurusname")

        self.actuator_name = self.get_property("actuator_name")
        if not self.name:
            logging.getLogger("HWR").info(
                "Undefined property actuator_name in xml. Applying name during instance creation."
            )
            self.actuator_name = self.name()

        self.threshold = self.get_property("threshold", self.threshold_default)
        logging.getLogger("HWR").debug(
            "Motor {0} threshold = {1}".format(self.actuator_name, self.threshold)
        )

        self.move_threshold = self.get_property(
            "move_threshold", self.move_threshold_default
        )
        logging.getLogger("HWR").debug(
            "Motor {0} move_threshold = {1}".format(
                self.actuator_name, self.move_threshold
            )
        )

        self.polling = self.get_property("interval", self.polling_default)
        logging.getLogger("HWR").debug(
            "Motor {0} polling = {1}".format(self.actuator_name, self.polling)
        )

        self.stop_command = self.add_command(
            {
                "type": "sardana",
                "name": self.actuator_name + SardanaMotor.suffix_stop,
                "taurusname": self.taurusname,
            },
            "Stop",
        )
        self.position_channel = self.add_channel(
            {
                "type": "sardana",
                "name": self.actuator_name + SardanaMotor.suffix_position,
                "taurusname": self.taurusname,
                "polling": self.polling,
            },
            "Position",
        )
        self.state_channel = self.add_channel(
            {
                "type": "sardana",
                "name": self.actuator_name + SardanaMotor.suffix_state,
                "taurusname": self.taurusname,
                "polling": self.polling,
            },
            "State",
        )

        self.velocity_channel = self.add_channel(
            {
                "type": "sardana",
                "name": self.actuator_name + SardanaMotor.suffix_velocity,
                "taurusname": self.taurusname,
            },
            "Velocity",
        )

        self.acceleration_channel = self.add_channel(
            {
                "type": "sardana",
                "name": self.actuator_name + SardanaMotor.suffix_acceleration,
                "taurusname": self.taurusname,
            },
            "Acceleration",
        )

        self.position_channel.connect_signal("update", self.motor_position_changed)
        self.state_channel.connect_signal("update", self.motor_state_changed)

        self.limits = self.get_limits()

        (self.limit_lower, self.limit_upper) = self.limits

        if self.limit_lower is None:
            self.limit_lower = self.static_limits[0]

        if self.limit_upper is None:
            self.limit_upper = self.static_limits[1]

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.motor_position_changed()
        elif signal == "stateChanged":
            self.motor_state_changed()

    def updateState(self):
        """
        Descript. : forces position and state update
        """
        self.motor_position_changed()
        self.motor_state_changed()

    def motor_state_changed(self, state=None):
        """
        Descript. : called by the state channels update event
                    checks if the motor is at it's limit,
                    and sets the new device state
        """
        motor_state = self.motor_state

        if state is None:
            state = self.state_channel.get_value()

        state = str(state)
        motor_state = SardanaMotor.state_map[state]

        if motor_state != MotorStates.DISABLED:
            if self.motor_position >= self.limit_upper:
                motor_state = MotorStates.HIGHLIMIT
            elif self.motor_position <= self.limit_lower:
                motor_state = MotorStates.LOWLIMIT

        self.set_ready(motor_state > MotorStates.DISABLED)

        if motor_state != self.motor_state:
            self.motor_state = motor_state
            self.emit("stateChanged", (motor_state,))

    def motor_position_changed(self, position=None):
        """
        Descript. : called by the position channels update event
                    if the position change exceeds threshold,
                    valueChanged is fired
        """
        if position is None:
            position = self.position_channel.get_value()
        if abs(self.motor_position - position) >= self.threshold:
            self.motor_position = position
            self.emit("valueChanged", (position,))
            self.motor_state_changed()

    def get_state(self):
        """
        Descript. : returns the current motor state
        """
        self.motor_state_changed()
        return self.motor_state

    def get_limits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        try:
            return (self.limit_lower, self.limit_upper)
        except Exception:
            return (None, None)

    def get_value(self):
        """
        Descript. : returns the current position
        """
        self.motor_position = self.position_channel.get_value()
        return self.motor_position

    def _set_value(self, value):
        """
        Descript. : move to the given position
        """
        # if abs(absolute_position - current_pos) > self.move_threshold_default:
        self.position_channel.set_value(value)

    def stop(self):
        """
        Descript. : stops the motor immediately
        """
        self.stop_command()

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.is_ready() and self.get_state() == MotorStates.MOVING

    motorIsMoving = is_moving

    def wait_end_of_move(self, timeout=None):
        """
        Descript. : waits till the motor stops
        """
        with Timeout(timeout):
            time.sleep(0.1)
            while self.is_moving():
                time.sleep(0.1)

    def get_velocity(self):
        try:
            return self.velocity_channel.get_value()
        except Exception:
            return None

    def set_velocity(self, value):
        self.velocity_channel.set_value(value)

    def get_acceleration(self):
        try:
            return self.acceleration_channel.get_value()
        except Exception:
            return None


def test_hwo(hwo):
    print(("Position for %s is: %s" % (hwo.username, hwo.get_value())))
    print(("Velocity for %s is: %s" % (hwo.username, hwo.get_velocity())))
    print(("Acceleration for %s is: %s" % (hwo.username, hwo.get_acceleration())))


#    print("Moving motor to %s" % newpos)
#    hwo.set_value(newpos, timeout=None)
#    while hwo.is_moving():
#        print "Moving"
#        time.sleep(0.3)
#    print("Movement done. Position is now: %s" % hwo.get_value())

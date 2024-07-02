import logging
import time
import enum
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.BaseHardwareObjects import HardwareObject, HardwareObjectState
from gevent import Timeout

"""
Interfaces Sardana Motor objects.
taurusname is the only obligatory property.

.. code-block:: xml

   <object class="SardanaMotor">
    <taurusname>dmot01</taurusname>
    <username>Dummy</username>
    <actuator_name>dummy_motor</actuator_name>
    <threshold>0.005</threshold>
    <move_threshold>0.005</move_threshold>
    <interval>2000</interval>
 </object>
"""


class SardanaMotorState(enum.Enum):
    READY = HardwareObjectState.READY
    ON = HardwareObjectState.READY
    OFF = HardwareObjectState.OFF
    MOVING = HardwareObjectState.BUSY
    STANDBY = HardwareObjectState.READY
    FAULT = HardwareObjectState.FAULT
    INIT = HardwareObjectState.BUSY
    RUNNING = HardwareObjectState.BUSY
    ALARM = HardwareObjectState.WARNING
    DISABLE = HardwareObjectState.OFF
    UNKNOWN = HardwareObjectState.UNKNOWN
    INVALID = HardwareObjectState.FAULT


class SardanaMotor(AbstractMotor):
    suffix_position = "Position"
    suffix_state = "State"
    suffix_stop = "Stop"
    suffix_velocity = "Velocity"
    suffix_acceleration = "Acceleration"

    def __init__(self, name):
        super().__init__(name)
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

    def init(self):
        super().init()

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

        self.position_channel.connect_signal("update", self.update_value)
        self.state_channel.connect_signal("update", self._update_state)

        self.limits = self.get_limits()
        self.update_state()
        self.update_value()

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum 'HardwareObjectState'): Motor state.
        """
        try:
            _state = self.state_channel.get_value()
            self.specific_state = _state
            return SardanaMotorState[_state.name].value
        except (KeyError, AttributeError):
            return self.STATES.UNKNOWN

    def _update_state(self, state):
        try:
            state = state.upper()
            state = SardanaMotorState[state].value
        except (AttributeError, KeyError):
            state = self.STATES.UNKNOWN
        return self.update_state(state)

    def is_ready(self):
        """
        Descript. : True if the motor is ready
        """
        return self.get_state() == HardwareObjectState.READY

    def wait_ready(self, timeout=None):
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            while not self.is_ready():
                time.sleep(0.1)

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.get_state() == HardwareObjectState.BUSY

    def wait_end_of_move(self, timeout=None):
        """
        Descript. : waits till the motor stops
        """
        with Timeout(timeout):
            # Wait a bit to ensure the motor started moving
            # 0.1 empirically obtained
            time.sleep(0.1)
            while self.is_moving():
                time.sleep(0.1)

    def get_limits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        try:
            self._nominal_limits = (
                self.position_channel.info.minval,
                self.position_channel.info.maxval,
            )
            return self._nominal_limits
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
        self.position_channel.set_value(value)

    def stop(self):
        """
        Descript. : stops the motor immediately
        """
        self.stop_command()

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

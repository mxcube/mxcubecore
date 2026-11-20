"""
Superclass for NICOS actuators.

Should be put as the first superclass,
e.g. class NICOSMotor(NICOSActuator, AbstractMotor):

Example of config file:

<object class="ESS.NICOSActuator">
    <host>my-nicos-server-hostname</host>
    <port>1234</port>
    <user>myuser</user>
    <password>mypassword</password>
    <device_name>my_nicos_moveable_device_name</device_name>
</object>
"""

import gevent
from gevent import monkey

gevent.monkey.patch_all()

from mxcubecore.HardwareObjects.abstract import AbstractActuator

from .nicos_connection import get_nicos_connected

CONN_CHECK_INTERVAL = 30


class NICOSActuator(AbstractActuator.AbstractActuator):
    """NICOS Actuator class

    Controls a NICOS EpicsAnalogMoveable device."""

    def __init__(self, name):
        super().__init__(name)
        self.__wait_actuator_task = None
        self._nominal_limits = (-1e4, 1e4)
        self.last_target_value = None
        self.ERROR_READBACK = 0

    def init(self):
        """Initialization method"""
        super(NICOSActuator, self).init()
        self.device_name = self.get_property("device_name")
        self._last_check = 0
        self.nicos_cli = None

        self.connect_to_nicos()
        if not self.check_nicos_connection():
            return

        self.MOVING = 0
        self.__watch_task = gevent.spawn(self._watch)
        self.update_state(self.STATES.READY)

    def connect_to_nicos(self):
        """Connect to NICOS server."""
        self.host = self.get_property("host")
        port = self.get_property("port")
        user = self.get_property("user")
        pw = self.get_property("password")  # TODO: Improve this to be safer.
        self.nicos_cli = get_nicos_connected(self.host, port, user, pw)

    def check_nicos_connection(self):
        """Check whether connection to NICOS server is successful or not, and
        print the result."""
        if not self.nicos_cli.is_connected():
            self.print_log(
                msg=f"Failed to connect to NICOS server ({self.host}, {self.device_name})."
            )
            return False
        self.print_log(
            msg=f"Successfully connected to NICOS server ({self.host}, {self.device_name})!"
        )
        return True

    def timer_expired(self):
        """Check whether timer expired or not."""
        return (gevent.time.monotonic() - self._last_check) >= CONN_CHECK_INTERVAL

    def timer_reset(self):
        """Reset timer."""
        self._last_check = gevent.time.monotonic()

    def retry_nicos_connection(self):
        """Retry connection to NICOS if needed."""
        if not self.timer_expired():
            return
        self.timer_reset()

        if self.nicos_cli.is_connected():
            self.print_log(
                msg=f"NICOS server connection still OK ({self.host}, {self.device_name})."
            )
            return

        self.print_log(
            msg=f"Retrying connection to NICOS server ({self.host}, {self.device_name})..."
        )
        self.connect_to_nicos()
        if not self.check_nicos_connection():
            self.print_log(
                msg=f"Retrying NICOS connection in {CONN_CHECK_INTERVAL}s ({self.host}, {self.device_name})."
            )

    def _watch(self):
        """Watch actuator current value and update it on the UI."""
        while True:
            gevent.time.sleep(0.3)
            self.update_value()
            # Manage ui state
            if self.ERROR_READBACK:
                self.update_state(self.STATES.FAULT)
                self.retry_nicos_connection()
            elif self.MOVING:
                self.update_state(self.STATES.BUSY)
                self.update_specific_state(self.SPECIFIC_STATES.MOVING)
            else:
                self.update_state(self.STATES.READY)

    def _wait_actuator(self):
        """Wait actuator to be at target."""
        self.MOVING = 1
        while not self.done_movement():
            gevent.time.sleep(0.3)
        self.update_specific_state(None)
        self.MOVING = 0

    def get_value(self):
        """Override AbstractActuator method."""
        readback_val = self.nicos_cli.get_dev_value(self.device_name)
        if readback_val is None:
            self.ERROR_READBACK = 1
            return 0
        self.ERROR_READBACK = 0
        return readback_val

    def _set_value(self, value):
        """Override AbstractActuator method."""
        self.last_target_value = value
        self.update_state(self.STATES.BUSY)

        line = "move('{}', {})".format(self.device_name, value)
        self.nicos_cli.run_command(line)

        self.__wait_actuator_task = gevent.spawn(self._wait_actuator)

    def abort(self):
        """Override HardwareObject method."""
        super().abort()
        line = "stop('{}')".format(self.device_name)
        self.nicos_cli.run_command(line)
        self.MOVING = 0
        self.reset()  # Clean state on NICOS

        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)

    def done_movement(self):
        """Return whether actuator is at target position or not."""
        if self.get_value() == self.last_target_value:
            return True
        return False

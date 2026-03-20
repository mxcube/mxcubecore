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
    <device_name>my_nicos_moveable_device</device_name>
</object>
"""

import time

import gevent
from gevent import monkey

from mxcubecore.HardwareObjects.abstract import AbstractActuator

from .nicos_connection import connect_to_nicos

monkey.patch_all()


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

        host = self.get_property("host")  # Create NICOS connection using the config
        port = self.get_property("port")
        user = self.get_property("user")
        pw = self.get_property("password")  # Improve this to be safer.
        self.device_name = self.get_property("device_name")
        self.nicos_cli = connect_to_nicos(host, port, user, pw)

        if not self.nicos_cli.is_connected():
            self.print_log(
                msg=f"Failed to connect to NICOS server ({host}, {self.device_name})."
            )
            return
        self.print_log(
            msg=f"Successfully connected to NICOS server ({host}, {self.device_name})."
        )

        self.MOVING = 0
        self.__watch_task = gevent.spawn(self._watch)
        self.update_state(self.STATES.READY)

    def _watch(self):
        """Watch actuator current value and update it on the UI."""
        while True:
            time.sleep(0.3)
            self.update_value()
            # Manage ui state
            if self.ERROR_READBACK:
                self.update_state(self.STATES.FAULT)
            elif self.MOVING:
                self.update_state(self.STATES.BUSY)
                self.update_specific_state(self.SPECIFIC_STATES.MOVING)
            else:
                self.update_state(self.STATES.READY)

    def _wait_actuator(self):
        """Wait actuator to be at target."""
        self.MOVING = 1
        while not self.done_movement():
            time.sleep(0.3)
        self.update_specific_state(None)
        self.MOVING = 0

    def get_value(self):
        """Override AbstractActuator method."""
        readback_val = self.nicos_cli.get_dev_param_value(self.device_name)
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
        self.nicos_cli.process_command(line)

        self.__wait_actuator_task = gevent.spawn(self._wait_actuator)

    def abort(self):
        """Override HardwareObject method."""
        super().abort()
        line = "stop('{}')".format(self.device_name)
        self.nicos_cli.process_command(line)
        self.MOVING = 0
        self.reset()  # Clean state on NICOS

        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)

    def done_movement(self):
        """Return whether actuator is at target position or not."""
        if self.get_value() == self.last_target_value:
            self.reset()
            return True
        return False

    def reset(self):
        """Reset NICOS device. This can be useful to be sure the device is in
        a health state on the NICOS side."""
        line = "reset('{}')".format(self.device_name)
        self.nicos_cli.process_command(line)

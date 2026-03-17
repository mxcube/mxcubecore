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
    <device_name>my_nicos_device</device_name>
</object>
"""

from gevent import monkey
monkey.patch_all()

import time
import copy
import gevent

from mxcubecore.HardwareObjects.abstract import AbstractActuator

from .nicos_connection import connect_to_nicos


class NICOSActuator(AbstractActuator.AbstractActuator):
    """NICOS actuator class
    
    This class is based on LNLS.EPICSActuator."""

    def __init__(self, name):
        super().__init__(name)
        self.__wait_actuator_task = None
        self._nominal_limits = (-1E4, 1E4)
        self.last_target_value = None
        self.ERROR_READBACK = 0

    def init(self):
        """ Initialization method """
        super(NICOSActuator, self).init()
        host = self.get_property("host") # Create NICOS connection using the config
        port = self.get_property("port")
        user = self.get_property("user")
        pw = self.get_property("password") # TODO: Improve this to be safer.
        self.nicos_cli = connect_to_nicos(host, port, user, pw)
        self.device_name = self.get_property("device_name")
        self.update_state(self.STATES.READY)

    def _wait_actuator(self):
        """ Wait actuator to be ready."""
        time.sleep(0.3)
        self.update_state(self.STATES.READY)

    def get_value(self):
        """ Override AbstractActuator method."""
        readback_val = self.nicos_cli.get_dev_param_value(self.device_name)
        if readback_val is None:
            self.ERROR_READBACK = 1
            return 0
        self.ERROR_READBACK = 0
        return readback_val

    def abort(self):
        """ Imediately halt movement. By default self.stop = self.abort"""
        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)
        
    def _set_value(self, value):
        """ Override AbstractActuator method."""
        self.last_target_value = value
        self.update_state(self.STATES.BUSY)

        line = "move('{}', {})".format(self.device_name, value)
        self.nicos_cli.process_command(line)

        self.__wait_actuator_task = gevent.spawn(self._wait_actuator)
        

"""
NICOS implementation of AbstractMotor.

Example of xml file:

<object class="ESS.NICOSMotor">
    <host>my-nicos-server-hostname</host>
    <port>1234</port>
    <user>myuser</user>
    <password>mypassword</password>
    <device_name>virtual_motor_2</device_name>
    <default_limits>(-10, 43)</default_limits>
</object>
"""

import logging
import time
import gevent

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.ESS.NICOSActuator import NICOSActuator


class NICOSMotor(NICOSActuator, AbstractMotor):
    """NICOS Motor class
    
    This class is based on LNLS.EPICSMotor."""

    def __init__(self, name):
        super().__init__(name)
        self._wrap_range = None

    def init(self):
        """ Initialization method."""
        super().init()
        self.__watch_task = gevent.spawn(self._watch)
        self.update_state(self.STATES.READY)
        self.moving = 0
    
    def _watch(self):
        """ Watch motor current value and update it on the UI."""
        while True:
            time.sleep(0.3)
            self.update_value()
            # Manage motor ui state
            if self.ERROR_READBACK:
                self.update_state(self.STATES.FAULT)
            elif self.moving:
                self.update_state(self.STATES.BUSY)
                self.update_specific_state(self.SPECIFIC_STATES.MOVING)
            else:
                self.update_state(self.STATES.READY)

    def _wait_actuator(self):
        """Override NICOSActuator method."""
        self.moving = 1
        while (not self.done_movement()):
            time.sleep(0.3)
        self.update_specific_state(None)
        self.moving = 0
    
    def reset(self):
        """Reset NICOS device. This can be useful to be sure the device is in 
        a health state."""
        line = "reset('{}')".format(self.device_name)
        self.nicos_cli.process_command(line)

    def abort(self):
        """Override NICOSActuator method."""
        line = "stop('{}')".format(self.device_name)
        ret = self.nicos_cli.process_command(line)
        self.moving = 0
        self.reset() 
        super().abort()
    
    def done_movement(self):
        """ Return whether motor finished movement or not."""
        if self.get_value() == self.last_target_value:
            self.reset()
            return True
        return False


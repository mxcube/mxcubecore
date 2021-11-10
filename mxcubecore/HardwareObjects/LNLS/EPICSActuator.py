"""
Superclass for EPICS actuators.

Should be put as the first superclass,
e.g. class EPICSMotor(EPICSActuator, AbstractMotor):

Example of xml file:

<device class="LNLS.EPICSActuator">
    <channel type="epics" name="epicsActuator_val">MNC:B:LUCIOLE01:LIGHT_CH1</channel>
    <channel type="epics" name="epicsActuator_rbv" polling="500">MNC:B:LUCIOLE01:LIGHT_CH1</channel>
    <username>BackLight</username>
    <motor_name>BackLight</motor_name>
    <default_limits>(0, 8000)</default_limits>
</device>
"""

import time
import random
import gevent
from mxcubecore.HardwareObjects.abstract import AbstractActuator


class EPICSActuator(AbstractActuator.AbstractActuator):
    """EPCIS actuator class"""

    ACTUATOR_VAL  = 'epicsActuator_val' # target
    ACTUATOR_RBV  = 'epicsActuator_rbv' # readback

    def __init__(self, name):
        super(EPICSActuator, self).__init__(name)
        self.__wait_actuator_task = None
        self._nominal_limits = (-1E4, 1E4)

    def init(self):
        """ Initialization method """
        super(EPICSActuator, self).init()
        self.update_state(self.STATES.READY)

    def _wait_actuator(self):
        """ Wait actuator to be ready."""
        time.sleep(0.3)
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Override AbstractActuator method."""
        return self.get_channel_value(self.ACTUATOR_RBV)

    def set_value(self, value, timeout=0):
        """ Override AbstractActuator method."""
        if self.read_only:
            raise ValueError("Attempt to set value for read-only Actuator")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            if timeout or timeout is None:
                with gevent.Timeout(
                    timeout, RuntimeError("Motor %s timed out" % self.username)
                ):
                    self._set_value(value)
                    new_value = self._wait_actuator(value)
            else:
                self._set_value(value)
                self.__wait_actuator_task = gevent.spawn(self._wait_actuator)
        else:
            raise ValueError("Invalid value %s; limits are %s"
                             % (value, self.get_limits())
                             )

    def abort(self):
        """Imediately halt movement. By default self.stop = self.abort"""
        if self.__wait_actuator_task is not None:
            self.__wait_actuator_task.kill()
        self.update_state(self.STATES.READY)
        
    def _set_value(self, value):
        """ Override AbstractActuator method."""
        self.set_channel_value(self.ACTUATOR_VAL, value)

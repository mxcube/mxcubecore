import time
import gevent
import math
import logging

from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from HardwareRepository.HardwareObjects.LNLS.EPICSActuator import EPICSActuator

MOTOR_DMOV = 'epicsMotor_dmov'
MOTOR_STOP = 'epicsMotor_stop'
MOTOR_RLV  = 'epicsMotor_rlv'
MOTOR_VELO = 'epicsMotor_velo'
MOTOR_DLLM = 'epicsMotor_dllm'
MOTOR_DHLM = 'epicsMotor_dhlm'
MOTOR_EGU  = 'epicsMotor_egu'

class LNLSMotor(EPICSActuator, AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self._wrap_range = None

    def init(self):
        """ Initialisation method """
        super(LNLSMotor, self).init()
        self.get_limits()
        self.get_velocity()
        self.update_state(self.STATES.READY)

    def _move(self, value):
        """Override super class method."""
        self.update_specific_state(self.SPECIFIC_STATES.MOVING)

        while (self.get_channel_value(MOTOR_DMOV) == 0):
            time.sleep(0.2)
            current_value = self.get_value()
            self.update_value(current_value)

        self.update_state(self.STATES.READY)
        return value

    def abort(self):
        """Override super class method."""
        self.set_channel_value(MOTOR_STOP, 1)
        if self.__move_task is not None:
            self.__move_task.kill()

    def get_limits(self):
        """Override super class method."""
        try:
            low_limit = float(self.get_channel_value(MOTOR_DLLM))
            high_limit = float(self.get_channel_value(MOTOR_DHLM))
            self._nominal_limits = (low_limit, high_limit)
        except:
            logging.getLogger("HWR").error('Error getting motor limits for: %s' % self.motor_name)
            # Set a default limit
            self._nominal_limits = (-1E4, 1E4)

        if self._nominal_limits == (0, 0) or self._nominal_limits == (float('-inf'), float('inf')):
            # Treat infinite limit values
            self._nominal_limits = (-1E4, 1E4)
            logging.getLogger("HWR").info('Motor %s: limits are %s. Considering them as %s.' % (self.motor_name, str(self._nominal_limits), str((-1E4, 1E4))))

        return self._nominal_limits

    def get_velocity(self):
        """Override super class method."""
        self._velocity = self.get_channel_value(MOTOR_VELO)
        return self._velocity

    def set_velocity(self, velocity):
        """Override super class method."""
        self.__velocity = self.set_channel_value(MOTOR_VELO, value)

    def validate_value(self, value):
        """Override super class method."""
        try:
            value = float(value)
        except Exception as e:
            pass
        if value is None:
            return True
        if math.isnan(value) or math.isinf(value):
            return False
        limits = self._nominal_limits
        if None in limits:
            return True
        return limits[0] <= value <= limits[1]

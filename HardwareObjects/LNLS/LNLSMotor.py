import time
import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

MOTOR_VAL  = 'epicsMotor_val'
MOTOR_RBV  = 'epicsMotor_rbv'
MOTOR_DMOV = 'epicsMotor_dmov'
MOTOR_STOP = 'epicsMotor_stop'
MOTOR_RLV  = 'epicsMotor_rlv'
MOTOR_VELO = 'epicsMotor_velo'
MOTOR_DLLM = 'epicsMotor_dllm'
MOTOR_DHLM = 'epicsMotor_dhlm'
MOTOR_EGU  = 'epicsMotor_egu'

class LNLSMotor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self._wrap_range = None
        #self.__move_task = None

    def init(self):
        """ Initialisation method """
        # get username, actuator_name and tolerance
        super(LNLSMotor, self).init()

        self.chan_motor_rbv = self.get_channel_object(MOTOR_RBV)
        if self.chan_motor_rbv is not None:
            self.chan_motor_rbv.connectSignal('update', self.position_changed)

        self.chan_motor_dmov = self.get_channel_object(MOTOR_DMOV)
        if self.chan_motor_dmov is not None:
            self.chan_motor_dmov.connectSignal('update', self.status_changed)

        self.update_state(self.STATES.READY)

    def _move(self, value):
        self.move(value)

    def move(self, position, wait=False, timeout=None):
        """Override super class method."""
        self.set_position(position)
        if wait:
            self.wait_end_of_move(0.1)
        else:
            self._move_task = gevent.spawn(self.wait_end_of_move, 0.1)

    def stop(self):
        """Override super class method."""
        self.setValue(MOTOR_STOP, 1)
        if self.__move_task is not None:
            self.__move_task.kill()

    def get_position(self):
        """Override super class method."""
        self.__position = self.get_channel_value(MOTOR_RBV)
        return self.__position

    def set_position(self, position):
        """Override super class method."""
        self.setValue(MOTOR_VAL, position)

    def position_changed(self, value):
        """Override super class method."""
        self.__position = position
        self.emit('positionChanged', (value))

    def status_changed(self, value):
        if (value == 0):
            self.update_specific_state(self.SPECIFIC_STATES.MOVING)
        elif (value == 1):
            self.update_state(self.STATES.READY)

    def wait_end_of_move(self, timeout=None):
        gevent.sleep(0.1)
        if (self.get_channel_value(MOTOR_DMOV) == 0):
            self.update_specific_state(self.SPECIFIC_STATES.MOVING)

        while (self.get_channel_value(MOTOR_DMOV) == 0):
            self.motorPosition = self.getPosition()
            self.emit('positionChanged', (self.motorPosition))
            gevent.sleep(0.1)
        self.update_state(self.STATES.READY)

    def get_limits(self):
        """Override super class method."""
        try:
            self.__limits = (self.get_channel_value(MOTOR_DLLM), self.get_channel_value(MOTOR_DHLM))
        except:
            logging.getLogger("HWR").error('Error getting motor limits for: %s' % self.motor_name)
            # Set a default limit
            self.__limits = (-1E4,1E4)

        return self.__limits

    def get_velocity(self):
        """Override super class method."""
        self.__velocity = self.get_channel_value(MOTOR_VELO)
        return self.__velocity

    def set_velocity(self, velocity):
        """Override super class method."""
        self.__velocity = self.setValue(MOTOR_VELO, value)

    def move_relative(self, relative_position, wait=False, timeout=None):
        """Override super class method."""
        self.setValue(MOTOR_RLV, relative_position)
        if (wait):
            self.wait_end_of_move(0.1)
        else:
            self._move_task = gevent.spawn(self.wait_end_of_move, 0.1)

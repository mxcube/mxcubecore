import logging
import time

from mxcubecore.HardwareObjects.LNLS.LNLSMotor import LNLSMotor


class LNLSDetDistMotor(LNLSMotor):

    PMAC_SENDCMD = 'pmac_sendcmd'

    def __init__(self, name):
        LNLSMotor.__init__(self, name)

    def _move(self, value):
        """Override super class method."""
        if not self.validate_value(value):
            raise ValueError("Invalid value %s; limits are %s"
                             % (value, self.get_limits())
                             )
        self.update_specific_state(self.SPECIFIC_STATES.MOVING)

        for i in range(2):
            logging.getLogger(
                "user_level_log").info('Setting detector distance...'
            )

        # Enable air
        logging.getLogger("HWR").info('%s: Enabling air' % self.motor_name)
        command = '#5,7,8j/'
        self.set_channel_value(self.PMAC_SENDCMD, command)
        time.sleep(2)

        # Wait for stability
        logging.getLogger("HWR").info('%s: Wait for air stability' % self.motor_name)
        while (self.get_channel_value(self.MOTOR_DMOV) == 0):
            time.sleep(0.2)
            current_value = self.get_value()
            self.update_value(current_value)

        # Move det dist motor
        logging.getLogger("HWR").info('%s: Set motor to %s' % (self.motor_name, value))
        self.set_channel_value(self.ACTUATOR_VAL, value)

        # Wait for movement
        logging.getLogger("HWR").info('%s: Wait for movement to finish' % self.motor_name)
        while (self.get_channel_value(self.MOTOR_DMOV) == 0
        or abs(current_value - value) > 0.0005):
            time.sleep(0.2)
            current_value = self.get_value()
            self.update_value(current_value)

        # Disable air
        time.sleep(1)
        logging.getLogger("HWR").info('%s: Disabling air' % self.motor_name)
        command = '#5,7,8dkill'
        self.set_channel_value(self.PMAC_SENDCMD, command)
        time.sleep(0.5)

        # Wait for stability
        logging.getLogger("HWR").info(
            '%s: Wait for air stability again' % self.motor_name
        )
        while (self.get_channel_value(self.MOTOR_DMOV) == 0):
            time.sleep(0.2)
            current_value = self.get_value()
            self.update_value(current_value)

        # Wait for stability
        logging.getLogger("HWR").info('%s: Movement done!' % self.motor_name)
        self.update_state(self.STATES.READY)
        for i in range(2):
            logging.getLogger(
                "user_level_log").info('Detector distance is set.'
            )
        return value

    def _set_value(self, value):
        """Override method."""
        # As this motor moves in a special way, we delegate its movement
        # sequence to _move.
        pass

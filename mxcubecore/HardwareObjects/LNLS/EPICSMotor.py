"""
EPICS implementation of AbstratMotor.
Example xml file:
<device class="LNLS.EPICSMotor">
    <channel type="epics" name="epicsActuator_val">SOL:S:m1.VAL</channel>
    <channel type="epics" name="epicsActuator_rbv" polling="500">SOL:S:m1.RBV</channel>
    <channel type="epics" name="epicsMotor_rlv">SOL:S:m1.RLV</channel>
    <channel type="epics" name="epicsMotor_dmov" polling="500">SOL:S:m1.DMOV</channel>
    <channel type="epics" name="epicsMotor_stop">SOL:S:m1.STOP</channel>
    <channel type="epics" name="epicsMotor_velo">SOL:S:m1.VELO</channel>
    <channel type="epics" name="epicsMotor_dllm">SOL:S:m1.DLLM</channel>
    <channel type="epics" name="epicsMotor_dhlm">SOL:S:m1.DHLM</channel>
    <channel type="epics" name="epicsMotor_egu">SOL:S:m1.EGU</channel>
    <username>Omega</username>
    <motor_name>Omega</motor_name>
    <unit>1e-3</unit>
    <GUIstep>90</GUIstep>
</device>
"""
import logging
import time

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.LNLS.EPICSActuator import EPICSActuator


class EPICSMotor(AbstractMotor, EPICSActuator):

    MOTOR_DMOV = 'epicsMotor_dmov'
    MOTOR_STOP = 'epicsMotor_stop'
    MOTOR_RLV = 'epicsMotor_rlv'
    MOTOR_VELO = 'epicsMotor_velo'
    MOTOR_DLLM = 'epicsMotor_dllm'
    MOTOR_DHLM = 'epicsMotor_dhlm'
    MOTOR_EGU = 'epicsMotor_egu'

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        EPICSActuator.__init__(self, name)
        self._wrap_range = None

    def init(self):
        """ Initialization method """
        AbstractMotor.init(self)
        EPICSActuator.init(self)
        self.get_limits()
        self.get_velocity()
        self.update_state(self.STATES.READY)

    def _move(self, value):
        """Override method."""
        self.update_specific_state(self.SPECIFIC_STATES.MOVING)

        while (self.get_channel_value(self.MOTOR_DMOV) == 0):
            time.sleep(0.2)
            current_value = self.get_value()
            self.update_value(current_value)

        self.update_state(self.STATES.READY)
        return value

    def abort(self):
        """Override method."""
        self.set_channel_value(self.MOTOR_STOP, 1)
        if self.__move_task is not None:
            self.__move_task.kill()

    def get_limits(self):
        """Override method."""
        try:
            low_limit = float(self.get_channel_value(self.MOTOR_DLLM))
            high_limit = float(self.get_channel_value(self.MOTOR_DHLM))
            self._nominal_limits = (low_limit, high_limit)
        except BaseException:
            self._nominal_limits = (None, None)

        if self._nominal_limits in [(0, 0), (float('-inf'), float('inf'))]:
            # Treat infinite limit
            self._nominal_limits = (None, None)
        
        logging.getLogger("HWR").info('Motor %s limits: %s' % (self.motor_name, self._nominal_limits))

        return self._nominal_limits

    def get_velocity(self):
        """Override method."""
        self._velocity = self.get_channel_value(self.MOTOR_VELO)
        return self._velocity

    def set_velocity(self, value):
        """Override method."""
        self.__velocity = self.set_channel_value(self.MOTOR_VELO, value)


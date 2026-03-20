"""
NICOS implementation of AbstractMotor.

Example of config file:

<object class="ESS.NICOSMotor">
    <host>my-nicos-server-hostname</host>
    <port>1234</port>
    <user>myuser</user>
    <password>mypassword</password>
    <device_name>my_nicos_motor_device</device_name>
    <default_limits>(-10, 43)</default_limits>
</object>
"""

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.ESS.NICOSActuator import NICOSActuator


class NICOSMotor(NICOSActuator, AbstractMotor):
    """NICOS Motor class

    Behaves just like a NICOS Actuator, but adapted to be a Motor in MXCuBE UI."""

    def __init__(self, name):
        super().__init__(name)

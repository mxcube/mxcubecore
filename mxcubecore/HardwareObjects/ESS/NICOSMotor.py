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
        



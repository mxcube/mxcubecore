# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from mxcubecore.HardwareObjects.abstract.AbstractMotor import (
    AbstractMotor,
    MotorStates,
)
from mxcubecore.HardwareObjects.SardanaMotor import SardanaMotor
from gevent import Timeout
import time

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__credits__ = ["ALBA"]
__version__ = "3."
__category__ = "General"

class XalocSardanaMotor(SardanaMotor):
    
    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.stop_command = None
        self.position_channel = None
        self.state_channel = None
        self.taurusname = None
        self.motor_position = 0.0
        self.last_position_emitted = 0.0
        self.threshold_default = 0.0018
        self.move_threshold_default = 0.0
        self.polling_default = "events"
        self.limit_upper = None
        self.limit_lower = None
        self.static_limits = (-1e4, 1e4)
        self.limits = (None, None)
        #RB: critical bug, NOTINITIALIZED is not a valid MotorStates
        #self.motor_state = MotorStates.NOTINITIALIZED
        self.motor_state = MotorStates.INITIALIZING
        
    def init(self):
        SardanaMotor.init(self)

    def motor_state_changed(self, state=None):
        """
        Descript. : called by the state channels update event
                    checks if the motor is at it's limit,
                    and sets the new device state
        """
        motor_state = self.motor_state

        if state is None:
            state = self.state_channel.get_value()

        state = str(state).strip("DevState.")
        motor_state = SardanaMotor.state_map[state]

        if motor_state != MotorStates.DISABLED:
            if self.motor_position >= self.limit_upper:
                motor_state = MotorStates.HIGHLIMIT
            elif self.motor_position <= self.limit_lower:
                motor_state = MotorStates.LOWLIMIT

        #self.set_ready(motor_state > MotorStates.DISABLED)

        if motor_state != self.motor_state:
            self.motor_state = motor_state
            self.emit("stateChanged", (motor_state,))

    def get_limits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        try:
            # RB: added the following three lines, since the limits were never properly initialized
            info = self.position_channel.get_info()
            self.limit_lower = info.minval
            self.limit_upper = info.maxval
            
            return (self.limit_lower, self.limit_upper)
        except Exception:
            return (None, None)
        
    def is_ready(self):
        return self.get_state() == MotorStates.READY
    
    def wait_ready(self, timeout=None):
        """Wait timeout seconds till SardanaMotor is ready.

        if timeout is None: wait forever.

        Args:
            timeout (s):

        Returns:
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for SardanaMotor status ready")):
            while not self.is_ready(): 
                time.sleep(0.05)
    
    def motor_position_changed(self, position=None):
        """
        Descript. : called by the position channels update event
                    if the position change exceeds threshold,
                    valueChanged is fired
        """
        if position is None:
            position = self.position_channel.get_value()
            self.last_position_emitted = position
        if abs(self.last_position_emitted - position) >= self.threshold:
            self.motor_position = position
            self.last_position_emitted = position
            self.emit("valueChanged", (position,))
            self.motor_state_changed()




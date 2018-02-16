#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import gevent

from AbstractMotor import AbstractMotor, MotorStates
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["The MxCuBE collaboration"]
__version__ = "2.3."
__category__ = "Motor"


"""
Example of xml config file

<device class="MotorMockup">
  <start_position>500</start_position>
  <velocity>100</velocity>
  <static_limits>[100, 1000]</static_limits>  
</device>
"""

class MotorMockup(AbstractMotor, HardwareObject):

    def __init__(self, name):
        AbstractMotor.__init__(self)
        HardwareObject.__init__(self, name)

        self.__move_task = None

    def init(self):
        try:
            self.move(float(self.getProperty("start_position")))
        except:
            self.move(10.124)

        try:
            self.set_velocity(float(self.getProperty("velocity")))
        except:
            self.set_velocity(100)

        try:
            self.set_limits(eval(self.getProperty("static_limits")))
        except:
            pass

    def is_ready(self):
        return True

    def set_ready(self, task):
        self.set_state(MotorStates.Ready)
        self.emit('stateChanged', (self.get_state(), ))

    def move(self, position, wait=False, timeout=None):
        self.set_state(MotorStates.Moving)
        self.__move_task = gevent.spawn(self.move_task, position)
        self.__move_task.link(self.set_ready)

    def move_task(self, position, wait=False, timeout=None):
        start_pos = self.get_position()
        if start_pos:
            delta = abs(position - start_pos)
            if position > self.get_position():
                direction = 1
            else:
                direction = -1
            start_time = time.time()
            self.emit('stateChanged', (self.get_state(), ))
            while (time.time() - start_time) < (delta / self.get_velocity()):
                self.set_position(start_pos + direction * self.get_velocity() * \
                                  (time.time() - start_time))
                self.emit('positionChanged', (self.get_position(), ))
                time.sleep(0.02)
        self.set_position(position)
        self.emit('positionChanged', (self.get_position(), ))

    def stop(self):
        if self.__move_task is not None:
            self.__move_task.kill()

    def update_values(self):
        self.emit('stateChanged', (self.get_state(), ))
        self.emit('positionChanged', (self.get_position(), ))

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

from AbstractMotor import AbstractMotor


__credits__ = ["The MxCuBE collaboration"]
__version__ = "2.3."
__category__ = "Motor"


"""
Example of xml config file

<device class="MotorMockup">
  <start_position>500</start_position>
  <velocity>100</velocity>
  <default_limits>[-360, 360]</default_limits>  
</device>
"""


DEFAULT_VELOCITY = 100
DEFAULT_LIMITS = (-360, 360)
DEFAULT_POSITION = 10.124


class MotorMockup(AbstractMotor):

    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.__move_task = None

    def init(self):
        try:
            self.set_velocity(float(self.getProperty("velocity")))
        except:
            self.set_velocity(DEFAULT_VELOCITY)

        try:
            self.set_limits(eval(self.getProperty("default_limits")))
        except:
            self.set_limits(DEFAULT_LIMITS)


        self.set_state(self.motor_states.READY)
        self.move(float(self.getProperty("start_position", DEFAULT_POSITION)))

    def move_task(self, position, wait=False, timeout=None):
        if position is None:
            # TODO is there a need to set motor position to None?
            return

        start_pos = self.get_position()
        if start_pos is not None:
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

    def move(self, position, wait=False, timeout=None):
        self.__motor_state = self.motor_states.MOVING
        if wait:
            self.set_position(position)
            self.emit('positionChanged', (self.get_position(), ))
            self.set_ready()
        else:
            self._move_task = gevent.spawn(self.move_task, position)
            self._move_task.link(self.set_ready)

    def stop(self):
        if self.__move_task is not None:
            self.__move_task.kill()

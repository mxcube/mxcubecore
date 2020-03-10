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

from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor


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
        except BaseException:
            self.set_velocity(DEFAULT_VELOCITY)

        try:
            self.set_limits(eval(self.getProperty("default_limits")))
        except BaseException:
            self.set_limits(DEFAULT_LIMITS)

        # self.set_state(self.motor_states.READY)
        self.set_value(float(self.getProperty("start_position", DEFAULT_POSITION)))

    def move_task(self, position, wait=False, timeout=None):
        if position is None:
            # TODO is there a need to set motor position to None?
            return

        start_pos = self.get_value()
        if start_pos is not None:
            delta = abs(position - start_pos)
            if position > self.get_value():
                direction = 1
            else:
                direction = -1
            start_time = time.time()
            self.emit("stateChanged", (self.get_state(),))
            while (time.time() - start_time) < (delta / self.get_velocity()):
                self.set_value(
                    start_pos
                    + direction * self.get_velocity() * (time.time() - start_time)
                )
                self.emit("positionChanged", (self.get_value(),))
                time.sleep(0.02)
        self.set_value(position)
        self.emit("positionChanged", (self.get_value(),))

    def move(self, position, wait=False, timeout=None):
        self.__motor_state = self.motor_states.MOVING
        if wait:
            self.set_value(position)
            self.emit("positionChanged", (self.get_value(),))
            self.set_ready()
        else:
            self._move_task = gevent.spawn(self.move_task, position)
            self._move_task.link(self.set_ready)

    def stop(self):
        if self.__move_task is not None:
            self.__move_task.kill()

    def get_value(self):
        """Read the actuator position.
        Returns:
            float: Actuator position.
        """
        return self._nominal_value

    def _set_value(self, value, timeout=None):
        """
        Implementation of specific set actuator logic.
        
        Args:
            value (float): target value
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait;
        """
        self._nominal_value = value

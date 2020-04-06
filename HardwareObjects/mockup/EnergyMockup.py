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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import ast
import time
import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy

# Default energy value (keV)
DEFAULT_VALUE = 12.4
# Default energy limits (keV)
DEFAULT_LIMITS = (4, 20)

class EnergyMockup(AbstractEnergy):
    def __init__(self, name):
        AbstractEnergy.__init__(self, name)
        self.__move_task = None

    def init(self):
        self.update_value(self.default_value or DEFAULT_VALUE)
        self.update_limits(
            ast.literal_eval(self.getProperty("energy_limits") or DEFAULT_LIMITS)
        )
        self.update_state(self.STATES.READY)


    def _move(self, value):
        """ Simulated energy change
        Args:
            value (float): target energy
        """
        start_pos = self.get_value()
        if value is not None and start_pos is not None:
            step = -1 if value < start_pos else 1
            for ii in range(int(start_pos) + step, int(value) + step, step):
                self.update_value(ii)
                time.sleep(0.2)
        return value

    def set_value(self, value, timeout=0):
        """
        Set energy to absolute value.
        This is NOT the recommended way, but for technical reasons
        overriding is necessary in this particular case
        Args:
            value (float): target value
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait (default);
                             if timeout is None: wait forever.
        Raises:
            ValueError: Value not valid or attemp to set read-only Energy.
        """
        if self.read_only:
            raise ValueError("Attempt to set value for read-only Energy")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            if timeout or timeout is None:
                with gevent.Timeout(
                    timeout, RuntimeError("Energy %s timed out" % self.username)
                ):
                    self._move(value)
                    self._set_value(value)
            else:
                self.__move_task = gevent.spawn(self._move, value)
                self.__move_task.link(self._callback)
        else:
            raise ValueError("Invalid value %s" % str(value))

    def _callback(self, move_task):
        value = move_task.get()
        self._set_value(value)

    def _set_value(self, value):
        """
        Implementation of specific set actuator logic.

        Args:
            value (float): target value
        """
        self.update_value(value)
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Read the energy value.
        Returns:
            float: energy value
        """
        return self._nominal_value

    def abort(self):
        """Imediately halt movement. By default self.stop = self.abort"""
        if self.__move_task is not None:
            self.__move_task.kill()
        self.update_state(self.STATES.READY)

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

import time

from HardwareRepository.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy


class EnergyMockup(AbstractEnergy):
    def __init__(self, name):
        AbstractEnergy.__init__(self, name)

    def init(self):
        self.tunable = True
        self._moving = False
        self._nominal_value = 12.7
        self.set_limits((4, 20))

    def set_value(self, value, wait=True):
        if wait:
            self._aborted = False
            self._moving = True

            # rhfogh: Modified as previous allowed only integer values
            # First move towards energy, setting to integer keV values
            step = -1 if value < self._nominal_value else 1
            for ii in range(int(self._nominal_value) + step, int(value) + step, step):
                if self._aborted:
                    self._moving = False
                    raise StopIteration("Energy change cancelled !")

                self._nominal_value = ii
                # self.update_values()
                time.sleep(0.2)

        # Now set final value
        self._set_value(value)
        self._moving = False
        # self.update_values()
        self.emit("stateChanged", ("ready"))

    def _set_value(self, value):
        self._nominal_value = value

    def get_value(self):
        return self._nominal_value

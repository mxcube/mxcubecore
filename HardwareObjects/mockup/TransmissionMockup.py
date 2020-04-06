# encoding: utf-8
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

from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects.abstract.AbstractTransmission import \
    AbstractTransmission


__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class TransmissionMockup(AbstractTransmission):
    """Transmission value as a percentage """

    def __init__(self, name):
        AbstractTransmission.__init__(self, name)

    def init(self):
        AbstractTransmission.init(self)
        self._nominal_value = self.default_value
        self.update_state(self.STATES.READY)

    def get_value(self):
        """
        Read the transmission value.

        Returns:
            Transmission value.
        """
        return self._nominal_value

    @task
    def _set_value(self, value):
        """
        Sets the hardware to target a given transmission.

        Args:
            value (float): target transmission value
        """
        self._nominal_value = value

    def abort(self):
        pass

    def get_state(self):
        """
        Returns the HardwareObject state.

        Returns:
            HardwareObjectState: current HardwareObject state
        """
        return self.STATES.READY

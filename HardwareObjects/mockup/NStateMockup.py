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

"""
Mockup AbstartNState implementation
Example xml file:
<device class="NStateMockup">
  <username>Mock InOut device</username>
  <actuator_name>mock_inout</actuator_name>
  <values>{"IN": "in", "OUT": "out"}</values>
</device>
"""
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class NStateMockup(AbstractNState):
    """Mock In/Out implementation of AbstartNState"""

    def __init__(self, name):
        AbstractNState.__init__(self, name)
        self.__saved_state = None

    def init(self):
        """Initialise the device"""
        AbstractNState.init(self)
        self.__saved_state = self.get_value()

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): Enum member, corresponding to the value or UNKNOWN.
        """

        return self._nominal_value

    def _set_value(self, value):
        """Set device to value.
        Args:
            value (Enum): target value
        """
        self._nominal_value = value
        self.__saved_state = value.name

    def get_state(self):
        """Get the device state.
        Returns:
            (Enum 'HardwareObjectState'): Device state.
        """
        _state = self._nominal_value
        if not _state:
            return self.STATES.UNKNOWN

        if _state in ("IN", "OUT"):
            if self.__saved_state == _state:
                _state = self.STATES.READY
            else:
                _state = self.STATES.BUSY
        else:
            _state = self.STATES.UNKNOWN
        return _state

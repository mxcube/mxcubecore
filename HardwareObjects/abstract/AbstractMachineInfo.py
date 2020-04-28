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

import abc

from HardwareRepository.BaseHardwareObjects import HardwareObject

class AbstractMachineInfo(HardwareObject):
    """Abstract machine info"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._current = None
        self._message = None
        self._lifetime = None
        self._topup_remaining = None
        self._values = {}

    def init(self):
        """Initialise some parameters."""
        pass

    @abc.abstractmethod
    def get_current(self):
        """Read current.
        Returns:
            value: Current.
        """
        return None

    def get_message(self):
        """Read message.
        Returns:
            value: Message.
        """
        return None

    def get_lifetime(self):
        """Read life time.
        Returns:
            value: Life time.
        """
        return None

    def get_topup_remaining(self):
        """Read top up remaining.
        Returns:
            value: Top up remaining.
        """
        return None

    @abc.abstractmethod
    def get_value(self):
        """Read machine info.
        Returns:
            value: dict
        """
        return None

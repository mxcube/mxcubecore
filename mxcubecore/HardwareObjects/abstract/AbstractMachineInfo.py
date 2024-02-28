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
"""Abstract machine info class"""

import abc

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractMachineInfo(HardwareObject):
    """Abstract machine info."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self._current = None
        self._message = None
        self._lifetime = None
        self._topup_remaining = None
        self._mach_info_dict = {}

    @abc.abstractmethod
    def get_current(self) -> float:
        """Read the ring current.
        Returns:
            Current [mA].
        """
        return 0

    def get_message(self) -> str:
        """Read the operator's message.
        Returns:
            Message.
        """
        return ""

    def get_lifetime(self) -> float:
        """Read the life time.
        Returns:
            Life time [s].
        """
        return 0

    def get_topup_remaining(self) -> float:
        """Read the top up remaining time.
        Returns:
            Top up remaining [s].
        """
        return 0

    def get_fill_mode(self) -> str:
        """Read the fill mode as text.
        Returns:
            Machine fille mode
        """
        return ""

    def get_mach_info_dict(self) -> dict:
        """Read machine info summary as dictionary.
        Returns:
            Copy of mach_info_dict.
        """
        return self._mach_info_dict.copy()

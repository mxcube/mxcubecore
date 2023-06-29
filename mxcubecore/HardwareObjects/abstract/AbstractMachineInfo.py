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

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
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
        """Read current.
        Returns:
            Current.
        """
        return 0

    def get_message(self) -> str:
        """
        Returns:
            Message.
        """
        return ""

    def get_lifetime(self) -> float:
        """
        Returns:
            Life time [s].
        """
        return 0

    def get_topup_remaining(self) -> float:
        """
        Returns:
            Top up remaining.
        """
        return 0

    def get_fill_mode(self) -> str:
        """
        Returns:
            Machine fille mode
        """
        return ""

    def get_mach_info_dict(self) -> dict:
        """
        Returns:
            Copy of mach_info_dict.
        """
        return self._mach_info_dict.copy()

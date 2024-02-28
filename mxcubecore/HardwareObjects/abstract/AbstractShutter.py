#
#  Project: MXCuBE
#  https://github.com/mxcube
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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

""" AbstractShutter class - interface for shutter type devices.
Define open/close methods and is_open property.
Overload BaseValueEnum
"""

import abc
from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright 2016-2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class BaseValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class AbstractShutter(AbstractNState):
    """Abstract base class for shutter type objects."""

    __metaclass__ = abc.ABCMeta
    VALUES = BaseValueEnum

    @property
    def is_open(self):
        """Check if the shutter is open.
        Returns:
            (bool): True if open, False otherwise.
        """
        return self.get_value() == self.VALUES.OPEN

    def open(self, timeout=None):
        """Open the shutter.
        Args:
            timeout(float): optional - timeout [s],
                            If timeout == 0: return at once and do not wait
                            if timeout is None: wait forever.
        """
        self.set_value(self.VALUES.OPEN, timeout=timeout)

    def close(self, timeout=None):
        """Close the shutter.
        Args:
            timeout(float): optional - timeout [s],
                            If timeout == 0: return at once and do not wait
                            if timeout is None: wait forever.
        """
        self.set_value(self.VALUES.CLOSED, timeout=timeout)

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
Defines BaseValueEnum and ShutterStates Enums.
"""

import abc
from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class BaseValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class AbstractShutter(AbstractNState):
    """Abstract base class for N state objects."""

    __metaclass__ = abc.ABCMeta
    VALUES = BaseValueEnum

    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def init(self):
        """Initilise the predefined values"""
        AbstractNState.init(self)

    def is_open(self):
        return self.get_value() == self.VALUES.OPEN

    def is_closed(self):
        return self.get_value() == self.VALUES.CLOSED

    def open(self):
        self.set_value(self.VALUES.OPEN)

    def close(self):
        self.set_value(self.VALUES.CLOSED)

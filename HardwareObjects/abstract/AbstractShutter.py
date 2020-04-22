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

""" AbstractShutter class - interface for N state devices.
Defines BaseValueEnum, initialise_values and value_to_enum methds.
Implements validate_value, set/update limits.
"""

import abc
from enum import Enum, unique
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState

from HardwareRepository.BaseHardwareObjects import HardwareObjectState

__copyright__ = """ Copyright 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class BaseValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    UNKNOWN = "UNKNOWN"


@unique
class ShutterStates(Enum):
    """Shutter states definitions."""

    OPEN = HardwareObjectState.READY, 6
    CLOSED = HardwareObjectState.READY, 7
    MOVING = HardwareObjectState.BUSY, 8
    DISABLED = HardwareObjectState.WARNING, 9
    AUTOMATIC = HardwareObjectState.READY, 10


class AbstractShutter(AbstractNState):
    """Abstract base class for N state objects."""

    __metaclass__ = abc.ABCMeta
    SPECIFIC_STATES = ShutterStates

    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def init(self):
        """Initilise the predefined values"""
        AbstractNState.init(self)

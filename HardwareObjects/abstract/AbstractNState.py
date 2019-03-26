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

"""
Defines the interface for N state devices
"""

import abc
from enum import Enum, unique
from HardwareRepository.BaseHardwareObjects import HardwareObject


class AbstractNState(object):
    """
    Abstract base class for N state objects.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def value_changed(self, value):
        """ Emitted on value change

        Args:
            value: (int)

        Emitts:
            shutterStateChanged: (str) state name
        """
        return

    @abc.abstractmethod
    def state(self):
        """
        Returns:
           str: The current state name 
        """
        return

    @abc.abstractmethod
    def is_valid(self):
        """ Checks if the shutter is in one of its predefined states """
        return

    @abc.abstractmethod
    def set_state(self, state, wait=False, timeout=None):
        """
        Args:
            state: (enum) The state to transition to
            wait: (bool) Wait for state transition to complete before returning
            timeout: (float) Raises TimeoutException if transition takes longer
                     than timeout seconds  
        """
        return


@unique
class ShutterState(Enum):
    """
    Defines the valid Shutter states
    """
    UNKOWN = 0
    CLOSED = 1
    OPEN = 2
    MOVING = 3
    AUTOMATIC = 4
    DISABLED = 5
    FAULT = -1
    ERROR = -2


class AbstractShutter(HardwareObject, AbstractNState):
    STATE = ShutterState

    def __init__(self, name):
        HardwareObject.__init__(self, name)

    @abc.abstractmethod
    def open(self, wait=False, timeout=None):
        """Opens shutter"""
        return

    @abc.abstractmethod
    def close(self, wait=False, timeout=None):
        """Closes shutter"""
        return

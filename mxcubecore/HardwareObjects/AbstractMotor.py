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

class MotorStates(object):
    """Enumeration of the motor states
    """
    Initializing = 0
    On           = 1
    Off          = 2
    Ready        = 3
    Busy         = 4
    Moving       = 5
    Standby      = 6
    Disabled     = 7
    Unknown      = 8
    Alarm        = 9
    Fault        = 10
    Invalid      = 11
    Offline      = 12
    LowLimit     = 13
    HighLimit    = 14

    STATE_DESC = {Initializing: "Initializing",
                  On: "On",
                  Off: "Off",
                  Ready: "Ready",
                  Busy: "Busy",
                  Moving: "Moving",
                  Standby: "Standby",
                  Disabled: "Disabled",
                  Unknown: "Unknown",
                  Alarm: "Alarm",
                  Fault: "Fault",
                  Invalid: "Invalid",
                  Offline: "Offline",
                  LowLimit: "LowLimit",
                  HighLimit: "HighLimit"}

    @staticmethod
    def tostring(state):
        return MotorStates.STATE_DESC.get(state, "Unknown")



class AbstractMotor(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.__state = MotorStates.Initializing
        self.__position = None
        self.__limits = (None, None)
        self.__velocity = None

    def is_ready(self):
        """
        Returns:
            bool: True if ready, otherwise False
        """
        return self.__state == MotorStates.tostring(MotorStates.Ready)

    def get_state(self):
        """Returns motoro state

        Returns:
            str: Motor state.
        """
        return self.__state

    def set_state(self, state):
        """Sets motor state

        Keyword Args:
            state (str): motor state
        """
        self.__state = state

    def get_position(self):
        """Read the motor user position.

        Returns:
            float: Motor position.
        """
        return self.__position

    def set_position(self, position):
        """Sets the motor position.

        Keyword Args:
            state (str): motor state
        """
        self.__position = position

    def get_limits(self):
        """Returns motor limits as (float, float)

        Returns:
            list: limits as a list with two floats
        """
        return self.__limits

    def set_limits(self, limits):
        """Sets motor limits

        Kwargs:
            limits (list): list with two floats
        """
        self.__limits = limits

    def get_velocity(self):
        """Returns velocity of the motor

        Returns:
            float. velocity
        """
        return self.__velocity

    def set_velocity(self, velocity):
        """Sets the velocity of the motor

        Kwargs:
            velocity (float): target velocity
        """
        self.__velocity = velocity

    @abc.abstractmethod
    def move(self, position, wait=False, timeout=None):
        """Move motor to absolute position.

        Kwargs:
            position (float): target position
            wait (bool): optional wait till motor finishes the movement
            timeout (float): optional seconds to wait till move finishes
        """
        return

    def move_relative(self, relative_position, wait=False, timeout=None):
        """Move to relative position. Wait the move to finish (True/False)

        Kwargs:
            relative_position (float): relative position to be moved
            wait (bool): optional wait till motor finishes the movement
            timeout (float): optional seconds to wait till move finishes
        """
        self.move(self.get_position() + relative_position, wait, timeout)

    @abc.abstractmethod
    def stop(self):
        """Stops the motor movement
        """
        return

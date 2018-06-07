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


from HardwareRepository.BaseHardwareObjects import HardwareObject


class MotorStates(object):
    """Enumeration of the motor states
    """
    INITIALIZING = 0
    ON           = 1
    OFF          = 2
    READY        = 3
    BUSY         = 4
    MOVING       = 5
    STANDBY      = 6
    DISABLED     = 7
    UNKNOWN      = 8
    ALARM        = 9
    FAULT        = 10
    INVALID      = 11
    OFFLINE      = 12
    LOWLIMIT     = 13
    HIGHLIMIT    = 14
    NOTINITIALIZED = 15
    MOVESTARTED  = 16
    
    STATE_DESC = {INITIALIZING: "Initializing",
                  ON: "On",
                  OFF: "Off",
                  READY: "Ready",
                  BUSY: "Busy",
                  MOVING: "Moving",
                  STANDBY: "Standby",
                  DISABLED: "Disabled",
                  UNKNOWN: "Unknown",
                  ALARM: "Alarm",
                  FAULT: "Fault",
                  INVALID: "Invalid",
                  OFFLINE: "Offline",
                  LOWLIMIT: "LowLimit",
                  HIGHLIMIT: "HighLimit",
                  NOTINITIALIZED: "NotInitialized",
                  MOVESTARTED: "MoveStated"}

    @staticmethod
    def tostring(state):
        return MotorStates.STATE_DESC.get(state, "Unknown")

    @staticmethod
    def fromstring(state_str):
        for key, value in MotorStates.STATE_DESC.items():
            if value == state_str:
                return key
        return MotorStates.STATE_DESC[MotorStates.UNKNOWN]


class AbstractMotor(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.motor_name = ""
        self.motor_states = MotorStates()
        self.__state = self.motor_states.INITIALIZING
        self.__position = None
        self.__limits = (None, None)
        self.__default_limits = (None, None)
        self.__velocity = None

    def isReady(self):
        #TODO remove this method
        #print ("Deprecation warning: Instead of isReady please call is_ready")
        return self.is_ready()

    def getPosition(self):
        #TODO remove this method
        #print ("Deprecation warning: Instead of getPosition please call get_position")
        return self.get_position()

    def getState(self):
        #TODO remove this method
        #print ("Deprecation warning: Instead of getState please call get_state")
        return self.get_state()

    def getLimits(self):
        #TODO remove this method
        #print ("Deprecation: Instead of getLimits please call get_limits")
        return self.get_limits()

    def getMotorMnemonic(self):
        #print "Call get_motor_mnemonic!!!"
        return self.get_motor_mnemonic()

    def get_motor_mnemonic(self):
        return self.motor_name

    def is_ready(self):
        """
        Returns:
            bool: True if ready, otherwise False
        """
        return self.__state == self.motor_states.READY

    def set_ready(self, task=None):
        """Sets motor state to ready"""
        self.set_state(self.motor_states.READY)

    def get_state(self):
        """Returns motor state

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
        self.emit('stateChanged', (state, ))

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
        self.emit('positionChanged', (position, ))

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
        self.emit('limitsChanged', (limits, ))

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

    def syncMoveRelative(self, position, timeout=None):
        self.move_relative(position, wait=True, timeout=timeout)

    def syncMove(self, position, timeout=None):
        self.move(position, wait=True, timeout=timeout)

    def stop(self):
        """Stops the motor movement
        """
        return

    def update_values(self):
        self.emit('stateChanged', (self.get_state(), ))
        self.emit('positionChanged', (self.get_position(), ))
        self.emit('limitsChanged', (self.get_limits(), ))

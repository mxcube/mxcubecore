#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Descript. : AbstractMotor represent motor.
"""

import abc

class AbstractMotor(object):
    __metaclass__ = abc.ABCMeta

    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
    EXPORTER_TO_MOTOR_STATE = { "Invalid": NOTINITIALIZED,
                                "Fault": UNUSABLE,
                                "Ready": READY,
                                "Moving": MOVING,
                                "Created": NOTINITIALIZED,
                                "Initializing": NOTINITIALIZED,
                                "Unknown": UNUSABLE,
                                "LowLim": ONLIMIT,
                                "HighLim": ONLIMIT,
                                "Offline": UNUSABLE}

    def __init__(self):
        """
        Descript. :
        """
        self.motor_state = AbstractMotor.NOTINITIALIZED
 
        self.static_limits = (-1E4, 1E4)
        self.limits = (None, None)

        #generic method used by the beamline setup
        self.get_value = self.getPosition

    def getMotorMnemonic(self):
        """
        Descript. :
        """
        return

    def updateState(self):
        """
        Descript. :
        """
        self.setIsReady(self.motor_state > AbstractMotor.UNUSABLE)

    @abc.abstractmethod
    def getState(self):
        """
        Return motor state
        """
        return

    @abc.abstractmethod
    def getLimits(self):
        """
        Returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        return

    @abc.abstractmethod
    def getPosition(self):
        """
        Read the motor user position.
        """
        return

    def getDialPosition(self):
        """
        Read the motor dial position.
        """
        return self.getPosition()

    @abc.abstractmethod
    def move(self, position, wait=False, timeout=None):
        """
        Move to absolute position. Wait the move to finish (True/False)
        """
        return

    def moveRelative(self, position, wait=False, timeout=None):
        """
        Move to relative position. Wait the move to finish (True/False)
        """
        return

    def syncMove(self, position, timeout=None):
        """
        Deprecated method - corresponds to move until move finished.
        """
        self.move(position, timeout=timeout, wait=True)

    def syncMoveRelative(self, position, timeout=None):
        """
        Deprecated method - corresponds to moveRelative until move finished.
        """
        self.moveRelative(position, timeout=timeout, wait=True)

    @abc.abstractmethod
    def stop(self):
        """
        Stop the motor
        """
        return

    def motorIsMoving(self):
        """
        Return True if the motor is moving, False otherwise
        """
        return


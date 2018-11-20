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


__author__ = "Jan Meyer"
__email__ = "jan.meyer@desy.de"
__copyright__ = "(c)2016 DESY, FS-PE, P11"
__license__ = "GPL"


import logging
from HardwareRepository.BaseHardwareObjects import Device
from AbstractMotor import AbstractMotor


class MotorWPositions(AbstractMotor, Device):
    """
    <device class="MotorWPositions">
        <username>Dummy</username>
        <motors>
            <object role="rolename" href="/dummy"></object>
        </motors>
        <deltas>
            <rolename>0.1</rolename>
        </deltas>
        <positions>
            <position>
                <name>Zoom 1X</name>
                <rolename>0.12</rolename>
            </position>
            <position>
                <name>Zoom 6X</name>
                <rolename>1.23</rolename>
            </position>
        </positions>
    </device>
    """

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        Device.__init__(self, name)
        self.predefined_positions = {}
        self.motor = None
        self.delta = 0.001
        self.positions = {}
        self._last_position_name = None

    def init(self):
        self._last_position_name = None
        try:
            roles = self["motors"].getRoles()
            role = roles[0]
            self.motor = self.getObjectByRole(role)
        except KeyError:
            logging.getLogger("HWR").error("MotorWPositions: motor not defined")
            return
        try:
            self.delta = self["deltas"].getProperty(role)
        except:
            logging.getLogger().info(
                "MotorWPositions: no delta defined, setting to %f", self.delta
            )
        try:
            positions = self["positions"]
        except:
            logging.getLogger().error("MotorWPositions: no positions defined")
        else:
            for position in positions:
                name = position.getProperty("name")
                pos = position.getProperty(role)
                self.predefined_positions[name] = pos
        self.connect(self.motor, "stateChanged", self.motor_state_changed)
        self.connect(self.motor, "positionChanged", self.motor_position_changed)
        self.setIsReady(self.motor.isReady())

    def getLimits(self):
        return (1, len(self.predefined_positions))

    def getPredefinedPositionsList(self):
        return sorted(self.predefined_positions.keys())
        # return self.predefined_positions

    def getCurrentPositionName(self, pos=None):
        if pos is None:
            pos = self.motor.getPosition()
        for (position_name, position) in self.predefined_positions.items():
            if self.delta >= abs(pos - position):
                return position_name
        return ""

    def moveToPosition(self, position_name):
        try:
            self.motor.move(self.predefined_positions[position_name])
        except:
            logging.getLogger("HWR").exception("MotorWPositions: invalid position name")

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError

    def getMotorMnemonic(self):
        """
        Descript. :
        """
        return self.motor_name

    def motor_state_changed(self, state):
        self.updateState(state)
        self.emit("stateChanged", (state,))

    def motor_position_changed(self, absolute_position=None):
        if absolute_position is None:
            absolute_position = self.motor.getPosition()
        position_name = self.getCurrentPositionName(absolute_position)
        if self._last_position_name != position_name:
            self._last_position_name = position_name
            self.emit(
                "predefinedPositionChanged",
                (position_name, position_name and absolute_position or None),
            )
        self.emit("positionChanged", (absolute_position,))

    def updateState(self, state=None):
        """
        Descript. :
        """
        if state is None:
            state = self.getState()
        self.setIsReady(state > AbstractMotor.UNUSABLE)

    def getState(self):
        """
        Descript. : return motor state
        """
        return self.motor.getState()

    def getPosition(self):
        """
        Descript. :
        """
        return self.motor.getPosition()

    def getDialPosition(self):
        """
        Descript. :
        """
        return self.motor.getDialPosition()

    def move(self, absolute_position):
        """
        Descript. :
        """
        self.motor.move(absolute_position)

    def moveRelative(self, relative_position):
        """
        Descript. :
        """
        self.motor.moveRelative(relative_position)

    def syncMove(self, absolute_position, timeout=None):
        """
        Descript. :
        """
        self.motor.syncMove(absolute_position, timeout)

    def syncMoveRelative(self, relative_position, timeout=None):
        """
        Descript. :
        """
        self.motor.syncMoveRelative(relative_position, timeout)

    def stop(self):
        """
        Descript. :
        """
        self.motor.stop()

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.motor.is_moving()

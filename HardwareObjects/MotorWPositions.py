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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging
from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__author__ = "Jan Meyer"
__email__ = "jan.meyer@desy.de"
__copyright__ = "(c)2016 DESY, FS-PE, P11"
__license__ = "GPL"


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
            roles = self["motors"].get_roles()
            role = roles[0]
            self.motor = self.get_object_by_role(role)
        except KeyError:
            logging.getLogger("HWR").error("MotorWPositions: motor not defined")
            return
        try:
            self.delta = self["deltas"].get_property(role)
        except Exception:
            logging.getLogger().info(
                "MotorWPositions: no delta defined, setting to %f", self.delta
            )
        try:
            positions = self["positions"]
        except Exception:
            logging.getLogger().error("MotorWPositions: no positions defined")
        else:
            for position in positions:
                name = position.get_property("name")
                pos = position.get_property(role)
                self.predefined_positions[name] = pos
        self.connect(self.motor, "stateChanged", self.motor_state_changed)
        self.connect(self.motor, "valueChanged", self.motor_position_changed)
        self.set_is_ready(self.motor.is_ready())

    def get_limits(self):
        return (1, len(self.predefined_positions))

    def getPredefinedPositionsList(self):
        return sorted(self.predefined_positions.keys())
        # return self.predefined_positions

    def get_current_position_name(self, pos=None):
        if pos is None:
            pos = self.motor.get_value()
        for (position_name, position) in self.predefined_positions.items():
            if self.delta >= abs(pos - position):
                return position_name
        return ""

    def moveToPosition(self, position_name):
        try:
            self.motor.set_value(self.predefined_positions[position_name])
        except Exception:
            logging.getLogger("HWR").exception("MotorWPositions: invalid position name")

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError

    def get_motor_mnemonic(self):
        """
        Descript. :
        """
        return self.actuator_name

    def motor_state_changed(self, state):
        self.updateState(state)
        self.emit("stateChanged", (state,))

    def motor_position_changed(self, absolute_position=None):
        if absolute_position is None:
            absolute_position = self.motor.get_value()
        position_name = self.get_current_position_name(absolute_position)
        if self._last_position_name != position_name:
            self._last_position_name = position_name
            self.emit(
                "predefinedPositionChanged",
                (position_name, position_name and absolute_position or None),
            )
        self.emit("valueChanged", (absolute_position,))

    def updateState(self, state=None):
        """
        Descript. :
        """
        if state is None:
            state = self.get_state()
        self.set_is_ready(state > AbstractMotor.UNUSABLE)

    def get_state(self):
        """
        Descript. : return motor state
        """
        return self.motor.get_state()

    def get_value(self):
        """
        Descript. :
        """
        return self.motor.get_value()

    def set_value(self, absolute_position, timeout=0):
        """
        Descript. :
        """
        self.motor.set_value(absolute_position, timeout)

    def set_value_relative(self, relative_position, timeout=0):
        """
        Descript. :
        """
        self.motor.set_value_relative(relative_position, timeout)

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

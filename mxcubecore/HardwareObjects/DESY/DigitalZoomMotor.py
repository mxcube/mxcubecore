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


__author__ = "Jan Meyer"
__email__ = "jan.meyer@desy.de"
__copyright__ = "(c)2016 DESY, FS-PE, P11"
__license__ = "GPL"


import logging
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from mxcubecore.HardwareObjects.abstract.AbstractMotor import MotorStates


class DigitalZoomMotor(AbstractMotor, HardwareObject):
    """
    Works with camera devices which provide
    zoom_exists, set_zoom, get_zoom and get_zoom_min_max
    <object class="DigitalZoomMotor">
        <username>Zoom</username>
        <actuator_name>Zoom</actuator_name>
        <object href="/mjpg-stream-video" role="camera"/>
    </object>
    """

    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        super().__init__(name)
        self.camera = None

    def init(self):
        self.set_limits((1.0, 1.0))
        try:
            self.camera = self.get_object_by_role("camera")
        except KeyError:
            logging.getLogger("HWR").warning("DigitalZoomMotor: camera not defined")
            return
        try:
            self.read_only = not (self.camera.zoom_exists())
        except AttributeError:
            self.read_only = True
        if not self.read_only:
            limits = self.camera.get_zoom_min_max()
            if limits[0] is None:
                limits[0] = -1000
            if limits[1] is None:
                limits[1] = 1000
            self.set_limits(limits)
            self.set_position(self.camera.get_zoom())
            self.update_state(self.STATES.READY)
        else:
            self.update_state(self.STATES.OFF)
            logging.getLogger("HWR").warning(
                "DigitalZoomMotor: digital zoom is not supported " "by camera object"
            )


    def update_state(self):
        """
        Descript. : forces position update
        """
        self.motor_position_changed()

    def motor_position_changed(self, position=None):
        """
        Descript. : called by move and updateState. if the position has
                    changed valueChanged is fired if the position is at one
                    of the limits the state is set accordingly on state
                    changes, stateChanged is fired
        """
        if position is None:
            if self.read_only:
                position = 1.0
            else:
                position = self.camera.get_zoom()

        if position != self.get_value():
            current_motor_state = self.get_state()
            if position <= self.get_limits()[0]:
                self.update_state(MotorStates.LOWLIMIT)
            elif position >= self.get_limits()[1]:
                self.update_state(MotorStates.HIGHLIMIT)
            else:
                current_motor_state = MotorStates.READY
            if (not self.read_only) and current_motor_state != self.get_state():
                self.update_state(current_motor_state)
                self.emit("stateChanged", (current_motor_state,))
            self.set_position(position)
            self.emit("valueChanged", (position,))

    #    def get_limits(self):
    #        """
    #        Descript. : returns motor limits. If no limits channel defined then
    #                    static_limits is returned
    #        """
    #        return self.limits

    def get_value(self):
        if self.read_only:
            self.motor_position = 1.0
        else:
            self.motor_position = self.camera.get_zoom()
        return self.motor_position

    def _set_value(self, value):
        """
        Descript. : move to the given position
        """
        self.camera.set_zoom(value)
        self.motor_position_changed(value)

    def stop(self):
        """
        Descript. : does nothing, for position change is instantaneous
        """

    def is_moving(self):
        return False

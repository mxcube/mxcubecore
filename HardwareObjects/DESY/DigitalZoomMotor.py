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


class DigitalZoomMotor(AbstractMotor, Device):
    """
    Works with camera devices which provide
    zoom_exists, set_zoom, get_zoom and get_zoom_min_max
    <device class="DigitalZoomMotor">
        <username>Zoom</username>
        <motor_name>Zoom</motor_name>
        <object href="/mjpg-stream-video" role="camera"/>
    </device>
    """

    def __init__(self, name):
        AbstractMotor.__init__(self)
        Device.__init__(self, name)
        self.camera = None
        self.limits = (1.0, 1.0)
        self.motor_position = 1.0
        self.zoom_supported = None

    def init(self):
        try:
            self.camera = self.getObjectByRole('camera')
        except KeyError:
            logging.getLogger("HWR").warning( \
                    "DigitalZoomMotor: camera not defined")
            return
        try:
            self.zoom_supported = self.camera.zoom_exists()
        except AttributeError:
            self.zoom_supported = False
        if self.zoom_supported:
            self.limits = self.camera.get_zoom_min_max()
            if self.limits[0] is None:
                self.limits[0] = self.static_limits[0]
            if self.limits[1] is None:
                self.limits[1] = self.static_limits[1]
            self.getPosition()
            self.motor_state = AbstractMotor.READY
        else:
            self.motor_state = AbstractMotor.UNUSABLE
            logging.getLogger("HWR").warning( \
                    "DigitalZoomMotor: digital zoom is not supported "
                    "by camera object")
        self.setIsReady(self.motor_state > AbstractMotor.UNUSABLE)

    def updateState(self):
        """
        Descript. : forces position update
        """
        self.motor_position_changed()

    def motor_position_changed(self, position=None):
        """
        Descript. : called by move and updateState. if the position has
                    changed positionChanged is fired if the position is at one
                    of the limits the state is set accordingly on state
                    changes, stateChanged is fired
        """
        if position is None:
            if self.zoom_supported:
                position = self.camera.get_zoom()
            else:
                position = 1.0
        if position != self.motor_position:
            motor_state = self.motor_state
            if position <= self.limits[0] or position >= self.limits[1]:
                motor_state = AbstractMotor.ONLIMIT
            else:
                motor_state = AbstractMotor.READY
            if self.zoom_supported and motor_state != self.motor_state:
                self.motor_state = motor_state
                self.emit('stateChanged', (motor_state, ))
            self.motor_position = position
            self.emit('positionChanged', (position, ))

    def getState(self):
        """
        Descript. : returns the current motor state
        """
        return self.motor_state

    def getLimits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        return self.limits

    def getPosition(self):
        """
        Descript. : returns the current position
        """
        if self.zoom_supported:
            self.motor_position = self.camera.get_zoom()
        else:
            self.motor_position = 1.0
        return self.motor_position

    def getDialPosition(self):
        """
        Descript. : not implemented i.e. identical to getPosition()
        """
        return self.getPosition()

    def move(self, absolute_position):
        """
        Descript. : move to the given position
        """
        if self.zoom_supported and absolute_position >= self.limits[0] and \
                absolute_position <= self.limits[1]:
            self.camera.set_zoom(absolute_position)
            self.motor_position_changed(absolute_position)

    def moveRelative(self, relative_position):
        """
        Descript. : move for the given distance
        """
        self.move(self.getPosition() + relative_position)

    def syncMove(self, absolute_position, timeout=None):
        """
        Descript. : same as normal move, for position change is instantaneous
        """
        self.move(absolute_position)

    def syncMoveRelative(self, relative_position, timeout=None):
        """
        Descript. : same as normal moveRelative, for position change is
                    instantaneous
        """
        self.syncMove(self.getPosition() + relative_position, timeout)

    def stop(self):
        """
        Descript. : does nothing, for position change is instantaneous
        """
        pass

    def is_moving(self):
        return False

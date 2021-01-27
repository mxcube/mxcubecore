# encoding: utf-8
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

from enum import Enum
import ast

from mxcubecore.hardware_objects.abstract.AbstractNState import AbstractNState
from mxcubecore.hardware_objects.abstract.AbstractNState import BaseValueEnum

class P11Zoom(AbstractNState):

    def __init__(self, name):
        self.camera_hwobj = None
        self.pixels_per_mm = None
        self.closest_zoom = None

        AbstractNState.__init__(self,name)

    def init(self):

        self.pixels_per_mm = self.get_property("pixels_per_mm")
        self.camera_hwobj = self.get_object_by_role("camera")

        self.connect(self.camera_hwobj, "zoomChanged", self.zoom_value_changed)

        if self.camera_hwobj is None:
            self.log.debug("P11Zoom.py - cannot connect to camera hardware object")
        else:
            self.log.debug("P11Zoom.py / current zoom is %s" % self.camera_hwobj.get_zoom())

        AbstractNState.init(self)

    def initialise_values(self):
        self.VALUES = Enum("ZoomEnum", ast.literal_eval(self.get_property('values')))

    def get_state(self):
        return self.STATES.READY

    def get_value(self):
        return self.get_zoom()

    def _set_value(self, value):
        self.set_zoom(value)

    def get_pixels_per_mm(self):
        current_zoom = self.get_zoom()
        px_per_mm = self.pixels_per_mm * current_zoom
        return [px_per_mm, px_per_mm]

    def get_zoom(self):
        self.log.debug("ZOOM: current zoom is : %s" % self.camera_hwobj.get_zoom())
        self.current_value = self.camera_hwobj.get_zoom()
        return self.current_value

    def set_zoom_value(self, value):
        self.camera_hwobj.set_zoom(value)

    def set_zoom(self,zoom):
        self.camera_hwobj.set_zoom(zoom.value)

    def get_current_zoom(self):
        self.get_zoom()
        self.update_zoom()
        return self.closest_zoom, self.get_zoom()

    def zoom_value_changed(self,value):
        self.log.debug("ZOOM - value changed: %s" % value)
        self.current_value = value
        self.update_value(value)
        self.update_zoom()

    def update_zoom(self):
        dist = None
        value = self.get_value()

        for zoom in self.VALUES:
            _dist = abs(value - zoom.value) 
            if dist is None or _dist < dist:
                dist = _dist 
                self.closest_zoom = zoom

        if self.closest_zoom is not None:
            self.emit("predefinedPositionChanged", (self.closest_zoom, value))
        else:
            self.emit("predefinedPositionChanged", (None, None))
          

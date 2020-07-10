
from enum import Enum
import ast

from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState
from HardwareRepository.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from HardwareRepository.utils.mxcube_logging import log

class P11Zoom(AbstractNState):

    def __init__(self, name):
        self.camera_hwobj = None
        self.pixels_per_mm = None
        self.closest_zoom = None

        AbstractNState.__init__(self,name)

    def init(self):

        self.pixels_per_mm = self.getProperty("pixels_per_mm")
        self.camera_hwobj = self.getObjectByRole("camera")

        self.connect(self.camera_hwobj, "zoomChanged", self.zoom_value_changed)

        if self.camera_hwobj is None:
            log.debug("P11Zoom.py - cannot connect to camera hardware object")
        else:
            log.debug("P11Zoom.py / current zoom is %s" % self.camera_hwobj.get_zoom())

        AbstractNState.init(self)

    def initialise_values(self):
        self.VALUES = Enum("ZoomEnum", ast.literal_eval(self.getProperty('values')))

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
        log.debug("ZOOM: current zoom is : %s" % self.camera_hwobj.get_zoom())
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
        log.debug("ZOOM - value changed: %s" % value)
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
          

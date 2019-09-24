from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMicroscope import (
    AbstractMicroscope,
)

class Microscope(AbstractMicroscope, HardwareObject):
    def __init__(self, name):
        AbstractMicroscope.__init__(self)
        HardwareObject.__init__(self, name)

    def init(self):
        self.camera_hwobj = self.getObjectByRole("camera")
        self.shapes_hwobj = self.getObjectByRole("shapes")
        self.focus_hwobj = self.getObjectByRole("focus")
        self.zoom_hwobj = self.getObjectByRole("zoom")
        self.frontlight_hwobj = self.getObjectByRole("frontlight")
        self.backlight_hwobj = self.getObjectByRole("backlight")
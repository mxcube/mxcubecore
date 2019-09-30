from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMicroscope import (
    AbstractMicroscope,
)

class Microscope(AbstractMicroscope, HardwareObject):
    def __init__(self, name):
        AbstractMicroscope.__init__(self)
        HardwareObject.__init__(self, name)

    def init(self):
        self._camera = self.getObjectByRole("camera")
        self._shapes = self.getObjectByRole("shapes")
        self._focus = self.getObjectByRole("focus")
        self._zoom = self.getObjectByRole("zoom")
        self._frontlight = self.getObjectByRole("frontlight")
        self._backlight = self.getObjectByRole("backlight")
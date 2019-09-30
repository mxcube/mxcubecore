from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)

class Pilatus(HardwareObject, AbstractDetector):
    def __init__(self, name):
        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)


    def init(self):
        self.distance_motor_hwobj = self.getObjectByRole("detector_distance")

    def has_shutterless(self):
        return True

    def default_mode(self):
        return 1

    def get_detector_mode(self):
        return self.default_mode()

    def set_detector_mode(self, mode):
        return

from mxcubecore.BaseHardwareObjects import HardwareObject


class Mar225(HardwareObject):
    def __init__(self, name):
        super().__init__(name)

    def init(self):
        pass

    def has_shutterless(self):
        return False

    def default_mode(self):
        return 1

    def get_detector_mode(self):
        return self.default_mode()

    def set_detector_mode(self, mode):
        return

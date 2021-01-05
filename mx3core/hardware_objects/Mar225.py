from mx3core.BaseHardwareObjects import Device


class Mar225(Device):
    def __init__(self, name):
        Device.__init__(self, name)

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

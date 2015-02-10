from HardwareRepository.BaseHardwareObjects import Device

class Pilatus(Device):      
    def __init__(self, name):
        Device.__init__(self, name)

    def init(self): 
        pass

    def has_shutterless(self):
        return True

    def get_detector_mode(self):
        return 0


from HardwareRepository.BaseHardwareObjects import Device

class AttenuatorsMockup(Device):
    def __init__(self, *args):
        Device.__init__(self, *args)

    def getAttState(self):
        return 0

    def getAttFactor(self):
        return 100

    def get_value(self):
        return self.getAttFactor()

    def set_value(self, value):
        return

from HardwareRepository.BaseHardwareObjects import Device


class AttenuatorsMockup(Device):
    def __init__(self, *args):
        Device.__init__(self, *args)
        self.value = 100
        self.emit("attFactorChanged", self.value)

    def is_ready(self):
        return True

    def getAttState(self):
        return 0

    def get_value(self):
        return self.value

    def _set_value(self, value):
        self.value = value
        self.emit("attFactorChanged", self.value)

    def re_emit_values(self):
        self.emit("attFactorChanged", self.value)

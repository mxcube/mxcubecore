from HardwareRepository.BaseHardwareObjects import Device


class TransmissionMockup(Device):
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels = []
        self.bits = []
        self.attno = 0
        self.value = 100

    def init(self):
        pass

    # remove following
    def getAttState(self):
        return 0

    # remove following
    def setAttFactor(self, value):
        self.value = value
        self.emit("valueChanged", self.value)

    def get_value(self):
        return self.value

    def _set_value(self, value):
        self.setAttFactor(value)

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    # remove following
    def attStateChanged(self, channelValue):
        pass

    # remove following
    def attFactorChanged(self, channelValue):
        pass

    def is_ready(self):
        return True

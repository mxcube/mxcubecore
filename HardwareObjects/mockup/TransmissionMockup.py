from HardwareRepository.BaseHardwareObjects import Device


class TransmissionMockup(Device):
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels = []
        self.bits = []
        self.attno = 0
        self.getValue = self.get_value
        self.value = 100

    def init(self):
        pass

    def getAttState(self):
        return 0

    def getAttFactor(self):
        return self.value

    def setAttFactor(self, value):
        self.value = value
        self.emit("valueChanged", self.value)

    def get_value(self):
        return self.getAttFactor()

    def set_value(self, value):
        self.setAttFactor(value)

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def attStateChanged(self, channelValue):
        pass

    def attFactorChanged(self, channelValue):
        pass

    def isReady(self):
        return True

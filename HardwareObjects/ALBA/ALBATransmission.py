
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device


class ALBATransmission(Device):
    def __init__(self, *args):
        Device.__init__(self, *args)
        self.transmission = None

    def init(self):
        self.transmissionChannel = self.getChannelObject("transmission")
        self.stateChannel = self.getChannelObject("state")

        self.transmissionChannel.connectSignal("update", self.transmissionChanged)
        self.stateChannel.connectSignal("update", self.stateChanged)

    def isReady(self):
        return True

    def transmissionChanged(self, value):
        self.transmission = value
        self.emit("attFactorChanged", self.transmission)

    def stateChanged(self, value):
        self.state = str(value)
        self.emit("attStateChanged", self.state)

    def getAttState(self):
        self.state = self.stateChannel.getValue()
        return self.state

    def getAttFactor(self):
        return self.get_value()

    def get_value(self):
        self.transmission = self.transmissionChannel.getValue()
        return self.transmission

    def set_value(self, value):
        self.transmission = value
        self.transmissionChannel.setValue(value)

    def setTransmission(self, value):
        self.set_value(value)

    def update_values(self):
        value = self.get_value()
        self.emit("attFactorChanged", value)


def test_hwo(hwo):
    print "Transmission is: ", hwo.get_value()

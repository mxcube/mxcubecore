from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class ALBATransmission(HardwareObject):
    def __init__(self, *args):
        Device.__init__(self, *args)
        self.transmission = None

    def init(self):
        self.transmissionChannel = self.get_channel_object("transmission")
        self.stateChannel = self.get_channel_object("state")

        self.transmissionChannel.connect_signal("update", self.transmissionChanged)
        self.stateChannel.connect_signal("update", self.stateChanged)

    def is_ready(self):
        return True

    def transmissionChanged(self, value):
        self.transmission = value
        self.emit("attFactorChanged", self.transmission)

    def stateChanged(self, value):
        self.state = str(value)
        self.emit("attStateChanged", self.state)

    def getAttState(self):
        self.state = self.stateChannel.get_value()
        return self.state

    def get_value(self):
        return self.transmissionChannel.get_value()

    def _set_value(self, value):
        self.transmissionChannel.set_value(value)

    def re_emit_values(self):
        value = self.get_value()
        self.emit("attFactorChanged", value)


def test_hwo(hwo):
    print("Transmission is: ", hwo.get_value())

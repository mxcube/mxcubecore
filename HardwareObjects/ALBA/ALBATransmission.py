from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import Device


class ALBATransmission(Device):
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
        self.state = self.stateChannel.getValue()
        return self.state

    def get_value(self):
        return self.transmissionChannel.getValue()

    def _set_value(self, value):
        self.transmissionChannel.setValue(value)

    def re_emit_values(self):
        value = self.get_value()
        self.emit("attFactorChanged", value)


def test_hwo(hwo):
    print("Transmission is: ", hwo.get_value())

import logging
from HardwareRepository.BaseHardwareObjects import Device


class PX1Attenuator(Device):
    stateAttenuator = {
        "ALARM": "error",
        "OFF": "error",
        "RUNNING": "moving",
        "MOVING": "moving",
        "STANDBY": "ready",
        "UNKNOWN": "changed",
        "EXTRACT": "extract",
        "INSERT": "insert",
    }

    def init(self):
        self.state_chan = self.getChannelObject("state")
        self.factor_chan = self.getChannelObject("parser")

        if self.state_chan is not None:
            self.state_chan.connectSignal("update", self.state_changed)

        if self.factor_chan is not None:
            self.factor_chan.connectSignal("update", self.factor_changed)

        self.connected()

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def getAttState(self, value=None):
        if not self.state_chan:
            return

        if value is None:
            value = self.state_chan.getValue()

        try:
            state_str = str(value)
            retval = self.stateAttenuator[state_str]
        except BaseException:
            value = None

        return retval

    def get_value(self):
        try:
            value = round(float(self.factor_chan.getValue()), 1)
        except BaseException:
            value = None

        return value

    def state_changed(self, value=None):
        state_value = self.getAttState(value)
        self.emit("attStateChanged", (state_value,))

    def factor_changed(self, channelValue):
        try:
            value = self.get_value()
        except BaseException:
            logging.getLogger("HWR").error(
                "%s attFactorChanged : received value on channel is not a float value",
                str(self.name()),
            )
        else:
            self.emit("attFactorChanged", (value,))

    def set_value(self, value):
        try:
            self.factor_chan.setValue(value)
        except BaseException:
            logging.getLogger("HWR").error(
                "%s set Transmission : received value on channel is not valid",
                str(self.name()),
            )
            value = None
        return value


def test_hwo(self):
    pass

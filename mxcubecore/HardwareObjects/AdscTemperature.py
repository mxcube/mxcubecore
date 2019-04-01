from HardwareRepository.HardwareObjects import TacoDevice


class AdscTemperature(TacoDevice.TacoDevice):
    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

    def init(self):
        if self.device.imported:
            self.setPollCommand("DevCCDGetHwPar", ["temp"])

            self.setIsReady(True)

    def valueChanged(self, deviceName, value):
        self.emit("valueChanged", (value,))

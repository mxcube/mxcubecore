import TacoDevice


class CyberStar(TacoDevice.TacoDevice):
    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

        self.idx = None
        self.scaling_factor = None

    def init(self):
        print(">>>", self.getProperty("scaling_factor"))
        self.idx = int(self.getProperty("idx") or 1)
        self.scaling_factor = float(self.getProperty("scaling_factor") or 1)

        if self.device.imported:
            self.setPollCommand("DevXbpmReadAll")

            self.setIsReady(True)

    def valueChanged(self, deviceName, values):
        value = values[6] * self.scaling_factor
        self.emit("valueChanged", "%g" % value)

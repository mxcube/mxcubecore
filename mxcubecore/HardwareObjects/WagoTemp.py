import logging

import TacoDevice


class WagoTemp(TacoDevice.TacoDevice):
    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

        self.wagoid = None
        self.wagoname = None
        self.wagochan = None

    def init(self):
        self.wagoname = str(self.getProperty("wagoname"))
        self.wagochan = int(self.getProperty("wagochan"))

        if self.device.imported:
            try:
                self.wagoid = self.device.DevName2Key(self.wagoname)
            except:
                logging.getLogger().exception(
                    "%s: cannot find id for wago %s", str(self.name()), self.wagoname
                )
            else:
                self.setPollCommand("DevReadPhys", self.wagoid)

                self.setIsReady(True)

    def valueChanged(self, deviceName, value):
        value = value[self.wagochan]

        self.emit("valueChanged", value)

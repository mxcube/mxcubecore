import math
import logging

import TacoDevice


class WagoCounter(TacoDevice.TacoDevice):
    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

        self.wagoid = None
        self.wagoname = None
        self.gainid = None
        self.value = None

    def init(self):
        self.wagoname = str(self.getProperty("wagoname")) + "_s"
        self.gainname = str(self.getProperty("wagoname")) + "_g"
        self.gainfactor = self.getProperty("gainfactor")

        if self.device.imported:
            try:
                self.wagoid = self.device.DevName2Key(self.wagoname)
                self.gainid = self.device.DevName2Key(self.gainname)
            except BaseException:
                logging.getLogger().exception(
                    "%s: cannot find id for wago %s", str(self.name()), self.wagoname
                )
            else:
                self.setPollCommand("DevReadPhys", self.wagoid)

                self.setIsReady(True)

    def getGain(self):
        try:
            gain = self.device.DevReadDigi(self.gainid)

            try:
                gn = gain.index(1) + 1
            except ValueError:
                gn = -1
        except BaseException:
            logging.getLogger().error("%s: cannot get gain", str(self.name()))
            return -1
        else:
            return gn

    def valueChanged(self, deviceName, value):
        value = value[0]

        gn = self.getGain()

        if gn < 0:
            # invalid gain
            value = None
        else:
            gain = math.pow(self.gainfactor, gn)
            value = gain * value

        # print self.device.devname," --> ", gain, "x", value, " = " ,gain*value

        self.emit("valueChanged", (value,))
        return value

    def getValue(self):
        return self.device.DevReadDigi(self.wagoid)

    def getPhysValue(self):
        return self.device.DevReadPhys(self.wagoid)

    def getCorrectedPhysValue(self):
        value = self.getPhysValue()[0]
        gn = self.getGain()

        if gn < 0:
            # invalid gain
            value = -9999
        else:
            gain = math.pow(self.gainfactor, gn)
            value = gain * value
        return value

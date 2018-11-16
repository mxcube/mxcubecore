import logging

import TacoDevice


class WagoPneu(TacoDevice.TacoDevice):
    states = {0: "out", 1: "in"}

    READ_CMD, READ_OUT = (0, 1)

    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

        # self.wagoidin  = None
        # self.wagoidout = None
        self.wagokyin = None
        self.wagokyout = None
        # self.logic     = 1
        # self.readmode  = WagoPneu.READ_OUT
        self.wagoState = "unknown"
        self.__oldValue = None

    def init(self):
        self.wagoidin = self.getProperty("wagoidin")
        self.wagoidout = self.getProperty("wagoidout")
        if self.getProperty("logic") is None:
            self.logic = 1
        readmode = self.getProperty("readmode")
        if readmode is None:
            self.readmode = WagoPneu.READ_OUT
        else:
            if readmode == "command":
                self.readmode = WagoPneu.READ_CMD
            else:
                self.readmode = WagoPneu.READ_OUT

        if self.device.imported:
            try:
                self.wagokyin = self.device.DevName2Key(self.wagoidin)

                if self.readmode == WagoPneu.READ_OUT:
                    self.wagokyout = self.device.DevName2Key(self.wagoidout)
            except:
                logging.getLogger("HWR").exception(
                    "%s: cannot find id for wago", self.name()
                )
            else:
                if self.readmode == WagoPneu.READ_OUT:
                    self.setPollCommand(
                        "DevReadNoCacheDigi", self.wagokyout
                    )  # (%s)[0]' % self.wagokyout)
                elif self.readmode == WagoPneu.READ_CMD:
                    self.setPollCommand(
                        "DevReadNoCacheDigi", self.wagokyin
                    )  # (%s)[0]' % self.wagokyin)

                self.setIsReady(True)

    def valueChanged(self, deviceName, value):
        value = value[0]
        if value == self.__oldValue:
            return
        else:
            self.__oldValue = value

        if str(self.logic) == "-1":
            value = abs(value - 1)

        if value in WagoPneu.states:
            self.wagoState = WagoPneu.states[value]
        else:
            self.wagoState = "unknown"

        self.emit("wagoStateChanged", (self.wagoState,))
        self.emit("actuatorStateChanged", (self.wagoState,))

    def getWagoState(self):
        return self.wagoState

    def getActuatorState(self, *args):
        return self.getWagoState()

    def wagoIn(self):
        if self.isReady():
            # self.argin = [ self.wagokyin, 0, 1 ]
            self.device.DevWriteDigi(
                [self.wagokyin, 0, 1]
            )  # executeCommand('DevWriteDigi(%s)' % str(self.argin))

    def actuatorIn(self):
        return self.wagoIn()

    def wagoOut(self):
        if self.isReady():
            # self.argin = [ self.wagokyin, 0, 0 ]
            self.device.DevWriteDigi(
                [self.wagokyin, 0, 0]
            )  # executeCommand('DevWriteDigi(%s)' % str(self.argin))

    def actuatorOut(self):
        return self.wagoOut()

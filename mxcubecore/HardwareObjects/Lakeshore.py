"""Lakeshore Hardware Object
"""
import TacoDevice
import logging
import time

# still have to find another solution
import qt

#


class Lakeshore(TacoDevice.TacoDevice):
    def init(self):
        self.__nb_connections = 0
        self.__timer = None

        self.ident = "?"
        self.n_channels = 0
        self.unit = "C"
        self.newInterval = True

        if self.device.imported:
            logging.getLogger("HWR").debug(
                "%s: serial line device server imported, going on", self.name()
            )

            self.device.DevSerFlush(2)
            self.device.DevSerSetParameter([3, 500, 4, 1, 5, 1, 6, 0, 7, 9600, 8, 13])
            self.ident = self.putget("*IDN?")

            if len(self.ident):
                self.setIsReady(True)

                self.n_channels = len(self.readChannels())
            else:
                logging.getLogger("HWR").error(
                    "%s: could not get ident. string from Lakeshore", self.name()
                )

    def setUnit(self, u):
        self.unit = u

    def getIdent(self):
        return self.ident

    def getChannelsNumber(self):
        return self.n_channels

    def setInterval(self, new_interval):
        self.interval = new_interval

        if self.__timer is not None and self.__nb_connections > 0:
            self.__timer.stop()
            self.newInterval = True
            self.__timer.start(new_interval)

    def connectNotify(self, signal):
        self.__nb_connections += 1

        if self.__nb_connections == 1:
            logging.getLogger("HWR").debug(
                "%s: starting polling on serial line Device Server %s",
                self.name(),
                self.tacoName(),
            )

            # start polling
            self.__timer = qt.QTimer(None)
            qt.QObject.connect(self.__timer, qt.SIGNAL("timeout()"), self.readChannels)
            self.__timer.start(self.interval)

    def disconnectNotify(self, signal):
        self.__nb_connections -= 1

        if self.__nb_connections == 0:
            logging.getLogger("HWR").debug("%s: stopping polling", self.name())
            self.__timer.stop()

    def putget(self, cmd, timeout=0):
        self.setStatus("reading...")

        self.device.DevSerWriteString("%s\r\n" % cmd)

        time.sleep(0.1)

        recv = ""
        ret = ""
        t0 = time.time()
        while not recv.endswith("\r\n"):
            recv = self.device.DevSerReadString(0)

            try:
                if len(recv) == 0:
                    # there is nothing to read
                    if timeout is not None and ((time.time() - t0) > timeout):
                        break
                    else:
                        print("waiting to read something", recv, len(recv))
                        time.sleep(0.05)
                else:
                    ret += recv
            except:
                ret = ""
                break

        time.sleep(0.05)

        if not ret.endswith("\r\n"):
            print(cmd, ret)
            logging.getLogger("HWR").error(
                "%s: received incomplete answer from Lakeshore", self.name()
            )
            self.setStatus("read error")
            return ""
        else:
            self.setStatus("idle")

        return ret.replace("\r\n", "")

    def setStatus(self, status):
        self.emit("statusChanged", status)

    def readChannels(self):
        if self.newInterval:
            self.newInterval = False
            self.emit("intervalChanged", self.interval)

        cmd = "%sRDG? 0" % self.unit

        reading = self.putget(cmd)

        try:
            channel_values = list(map(float, reading.split(",")))
        except ValueError:
            channel_values = []
        else:
            self.emit("channelsUpdate", channel_values)

        return channel_values

    def reset(self):
        if self.isReady():
            try:
                if self.__nb_connections > 0:
                    self.__timer.stop()

                logging.getLogger("HWR").debug("%s: resetting instrument", self.name())

                self.setStatus("resetting instrument, please wait...")

                self.device.DevSerFlush(2)

                self.device.DevSerWriteString("*RST\r\n")

                while True:
                    try:
                        ret = int(self.putget("*OPC?", timeout=None))
                    except ValueError:
                        break
                    else:
                        if ret == 1:
                            self.setStatus("resetting done !")
                            break
                        else:
                            self.setStatus("waiting for reset to be finished")
            finally:
                if self.__nb_connections > 0:
                    self.__timer.start(self.interval)
        else:
            self.setStatus("cannot talk to device !")

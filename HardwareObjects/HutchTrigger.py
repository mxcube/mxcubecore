from HardwareRepository import BaseHardwareObjects
import logging

import TacoDevice

try:
    import PyTango
except ImportError:
    logging.getLogger("HWR").warning(
        "HutchTrigger: PyTango not found: Tango PSS device servers cannot be reached"
    )

import qt


class TacoHutchTrigger(TacoDevice.TacoDevice):
    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

    def findPSSNumber(self, card, channel):
        return ((card - 1) * 4) + (channel - 1)

    def init(self):
        self.initialized = False
        self.__oldValue = None

        cmdHutchTrigger = self.getCommandObject("macro")
        cmdHutchTrigger.connectSignal("connected", self.connected)
        cmdHutchTrigger.connectSignal("disconnected", self.disconnected)
        cmdHutchTrigger.connectSignal("commandBeginWaitReply", self.macroStarted)
        cmdHutchTrigger.connectSignal("commandReplyArrived", self.macroDone)
        cmdHutchTrigger.connectSignal("commandFailed", self.macroFailed)
        # cmdHutchTrigger.connectSignal('commandAborted', self.macroDone)

        try:
            chanStatus = self.getChannelObject("status")
            chanStatus.connectSignal("update", self.statusChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot report status", self.name())

        try:
            chanMsg = self.getChannelObject("msg")
            chanMsg.connectSignal("update", self.msgChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot show messages", self.name())

        PSSinfo = self.getProperty("pss")
        try:
            card, channel = list(map(int, PSSinfo.split("/")))
        except:
            logging.getLogger().error("%s: cannot find PSS number", self.name())
            return
        else:
            self.pssNumber = self.findPSSNumber(card, channel)

        if self.device.imported:
            self.setPollCommand("DevReadSigValues")

        if cmdHutchTrigger.isConnected():
            self.connected()

    def isConnected(self):
        return self.getCommandObject("macro").isConnected()

    def connected(self):
        if self.device.imported:
            self.setIsReady(True)

        self.emit("connected")

    def disconnected(self):
        self.emit("disconnected")
        self.setIsReady(False)

    def macroStarted(self, *args):
        self.emit("macroStarted")

    def macroDone(self, *args):
        self.emit("macroDone")

    def macroFailed(self, *args):
        self.emit("macroFailed")

    def abort(self):
        cmdHutchTrigger = self.getCommandObject("macro")
        cmdHutchTrigger.abort()

    def msgChanged(self, channelValue):
        self.emit("msgChanged", (channelValue,))

    def statusChanged(self, channelValue):
        self.emit("statusChanged", (channelValue,))

    def valueChanged(self, deviceName, value):
        value = value[self.pssNumber]

        if value == self.__oldValue:
            return
        else:
            self.__oldValue = value

        if value == 0:
            if self.initialized:
                self.emit("hutchTrigger", (1,))
        elif value == 1 and self.initialized:
            self.emit("hutchTrigger", (0,))

        self.initialized = True


class TangoHutchTrigger(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def _init(self):
        try:
            self.device = PyTango.DeviceProxy(self.getProperty("tangoname"))
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None
            self.device.imported = False
        else:
            self.device.imported = True

        self.pollingTimer = None
        self.initialized = False
        self.__oldValue = None
        self.card = None
        self.channel = None

    def init(self):
        cmdHutchTrigger = self.getCommandObject("macro")
        cmdHutchTrigger.connectSignal("connected", self.connected)
        cmdHutchTrigger.connectSignal("disconnected", self.disconnected)
        cmdHutchTrigger.connectSignal("commandBeginWaitReply", self.macroStarted)
        cmdHutchTrigger.connectSignal("commandReplyArrived", self.macroDone)
        cmdHutchTrigger.connectSignal("commandFailed", self.macroFailed)
        # cmdHutchTrigger.connectSignal('commandAborted', self.macroDone)

        try:
            chanStatus = self.getChannelObject("status")
            chanStatus.connectSignal("update", self.statusChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot report status", self.name())

        try:
            chanMsg = self.getChannelObject("msg")
            chanMsg.connectSignal("update", self.msgChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot show messages", self.name())

        PSSinfo = self.getProperty("pss")
        try:
            self.card, self.channel = list(map(int, PSSinfo.split("/")))
        except:
            logging.getLogger().error("%s: cannot find PSS number", self.name())
            return

        if self.device is not None:
            self.pollingTimer = qt.QTimer()
            self.pollingTimer.connect(
                self.pollingTimer, qt.SIGNAL("timeout()"), self.poll
            )
            self.pollingTimer.start(self.getProperty("interval") or 500)

        if cmdHutchTrigger.isConnected():
            self.connected()

    def isConnected(self):
        return self.getCommandObject("macro").isConnected()

    def connected(self):
        if self.device.imported:
            self.setIsReady(True)

        self.emit("connected")

    def disconnected(self):
        self.emit("disconnected")
        self.setIsReady(False)

    def macroStarted(self, *args):
        self.emit("macroStarted")

    def macroDone(self, *args):
        self.emit("macroDone")

    def macroFailed(self, *args):
        self.emit("macroFailed")

    def abort(self):
        cmdHutchTrigger = self.getCommandObject("macro")
        cmdHutchTrigger.abort()

    def msgChanged(self, channelValue):
        self.emit("msgChanged", (channelValue,))

    def statusChanged(self, channelValue):
        self.emit("statusChanged", (channelValue,))

    def poll(self):
        a = self.device.GetInterlockState([self.card - 1, 2 * (self.channel - 1)])[0]
        b = self.device.GetInterlockState([self.card - 1, 2 * (self.channel - 1) + 1])[
            0
        ]
        value = a & b

        if value == self.__oldValue:
            return
        else:
            self.__oldValue = value

        self.valueChanged(value)

    def valueChanged(self, value, *args):
        if value == 0:
            if self.initialized:
                self.emit("hutchTrigger", (1,))
        elif value == 1 and self.initialized:
            self.emit("hutchTrigger", (0,))

        self.initialized = True


class HutchTrigger(BaseHardwareObjects.Device):
    def _init(self):
        if self.getProperty("taconame"):
            self.__class__ = TacoHutchTrigger
            self._init()
        elif self.getProperty("tangoname"):
            self.__class__ = TangoHutchTrigger
            self._init()

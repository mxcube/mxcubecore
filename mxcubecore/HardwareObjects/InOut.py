import logging
from HardwareRepository.BaseHardwareObjects import Device


class InOut(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.wagoState = "unknown"

    def init(self):
        self.statechan = self.getChannelObject("state")
        self.statechan.connectSignal("update", self.valueChanged)
        self.statechan.connectSignal("connected", self._setReady)
        self.statechan.connectSignal("disconnected", self._setReady)
        self.set_in = self.getCommandObject("set_in")
        self.set_in.connectSignal("connected", self._setReady)
        self.set_in.connectSignal("disconnected", self._setReady)
        self.set_out = self.getCommandObject("set_out")
        self._setReady()
        self.offset = self.getProperty("offset")
        if self.offset > 0:
            self.states = {self.offset: "out", self.offset - 1: "in"}
        else:
            self.states = {0: "out", 1: "in", True: "in", False: "out"}
        self.private = {}
        private = self.getProperty("private_state")
        if private is None:
            pass
        else:
            import ast

            self.private = ast.literal_eval(private)

    def _setReady(self):
        # logging.getLogger().info("---------------------------- %s %s %s", self.set_in, self.statechan.isConnected(), self.set_in.isConnected())
        self.setIsReady(self.statechan.isConnected() and self.set_in.isConnected())

    def connectNotify(self, signal):
        if signal == "wagoStateChanged":
            if self.isReady():
                self.valueChanged(self.statechan.getValue())

    def valueChanged(self, value):
        self.wagoState = self.private.get(value, "unknown")
        if self.wagoState == "unknown":
            self.wagoState = self.states.get(value, "unknown")
        # logging.getLogger().info("wagostate change %s %s %s: ", self.set_in, self.wagoState, value)
        self.emit("wagoStateChanged", (self.wagoState,))

    def getWagoState(self):
        if self.wagoState == "unknown":
            self.connectNotify("wagoStateChanged")

        # logging.getLogger().info("wagostate get %s  %s: ",self.set_in, self.wagoState)
        return self.wagoState

    def wagoIn(self):
        self._setReady()
        if self.isReady():
            self.set_in()

    def wagoOut(self):
        self._setReady()
        if self.isReady():
            self.set_out()

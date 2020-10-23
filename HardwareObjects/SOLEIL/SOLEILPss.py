# -*- coding: utf-8 -*-
import logging
import time
from HardwareRepository.BaseHardwareObjects import Device
from PyTango import DeviceProxy

"""Complex means we are not using SimpleDevice"""


class SOLEILPss(Device):
    states = {0: "not ready", 1: "ready"}

    READ_CMD, READ_OUT = (0, 1)

    def __init__(self, name):
        Device.__init__(self, name)

        self.wagoState = "unknown"
        self.__oldValue = None
        self.device = None
        self.hutch = None

    def init(self):
        try:
            self.device = DeviceProxy(self.getProperty("tangoname"))
        except Exception:
            logging.getLogger("HWR").error(
                "%s: unknown pss device name", self.getProperty("tangoname")
            )

        if self.getProperty("hutch") not in ("optical", "experimental"):
            logging.getLogger("HWR").error(
                "SOLEILPss.init Hutch property %s is not correct",
                self.getProperty("hutch"),
            )
        else:
            self.hutch = self.getProperty("hutch")
            self.stateChan = self.get_channel_object("State")
            self.stateChan.connectSignal("update", self.valueChanged)
        if self.device:
            self.setIsReady(True)

    def get_state(self, value):
        return SOLEILPss.states[value]

    def getWagoState(self):
        return self.get_state(self.stateChan.getValue())

    def valueChanged(self, value):
        logging.getLogger("HWR").info(
            "%s: SOLEILPss.valueChanged, %s", self.name(), value
        )
        state = self.get_state(value)
        self.emit("wagoStateChanged", (state,))

# -*- coding: utf-8 -*-
import logging
import time
from mxcubecore.BaseHardwareObjects import HardwareObject
from PyTango import DeviceProxy

"""Complex means we are not using SimpleDevice"""


class SOLEILPss(HardwareObject):
    states = {0: "not ready", 1: "ready"}

    READ_CMD, READ_OUT = (0, 1)

    def __init__(self, name):
        super().__init__(name)

        self.wagoState = "unknown"
        self.__oldValue = None
        self.device = None
        self.hutch = None

    def init(self):
        try:
            self.device = DeviceProxy(self.get_property("tangoname"))
        except Exception:
            logging.getLogger("HWR").error(
                "%s: unknown pss device name", self.get_property("tangoname")
            )

        if self.get_property("hutch") not in ("optical", "experimental"):
            logging.getLogger("HWR").error(
                "SOLEILPss.init Hutch property %s is not correct",
                self.get_property("hutch"),
            )
        else:
            self.hutch = self.get_property("hutch")
            self.stateChan = self.get_channel_object("State")
            self.stateChan.connect_signal("update", self.value_changed)
        if self.device:
            self.set_is_ready(True)

    def get_state(self, value):
        return SOLEILPss.states[value]

    def getWagoState(self):
        return self.get_state(self.stateChan.get_value())

    def value_changed(self, value):
        logging.getLogger("HWR").info(
            "%s: SOLEILPss.valueChanged, %s", self.name(), value
        )
        state = self.get_state(value)
        self.emit("wagoStateChanged", (state,))

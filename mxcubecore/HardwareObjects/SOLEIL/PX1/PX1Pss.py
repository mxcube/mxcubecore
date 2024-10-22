# -*- coding: utf-8 -*-
import logging

from mxcubecore.BaseHardwareObjects import HardwareObject


class PX1Pss(HardwareObject):

    states = {0: "not ready", 1: "ready"}

    def init(self):
        self.state_chan = self.get_channel_object("state")
        self.state_chan.connect_signal("update", self.value_changed)

    def value_changed(self, value):
        state = self.get_state(value)
        logging.getLogger("HWR").debug("state changed. value is %s" % state)
        self.emit("stateChanged", (state,))

    def get_state(self, value=None):
        if value is None:
            value = self.state_chan.get_value()

        if value in self.states:
            self.state = self.states[value]
        else:
            self.state = "unknown"

        return self.state


def test_hwo(hwo):
    print(hwo.get_state())

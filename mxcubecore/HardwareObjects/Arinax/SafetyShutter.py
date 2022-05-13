# -*- coding: utf-8 -*-
"""

XML Configuration Example:

* With state attribute and open/close commands

<device class = "Arinax.SafetyShutter">
  <username>FrontEnd</username>
  <command type="epics" name="Open">Open</command>
  <command type="epics" name="Close">Close</command>
  <channel type="epics" name="State">State</channel>
</device>

* With read/write attribute :

<device class = "Arinax.SafetyShutter">
  <username>Safety Shutter</username>
  <channel type="epics" name="safetyShutterState">Epics PV</channel>
</device>

"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository import BaseHardwareObjects

import logging


class SafetyShutter(BaseHardwareObjects.Device):

    shutterState = {
        "3": "unknown",
        "1": "closed",
        "0": "opened",
    }

    def init(self):
        self.state_value_str = "unknown"
        try:
            self.shutter_channel = self.get_channel_object("safetyShutterState")
            self.shutter_channel.connectSignal("update", self.shutterStateChanged)
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot connect to shutter channel", self.name()
            )

        self.open_cmd = self.get_command_object("Open")
        self.close_cmd = self.get_command_object("Close")

    def shutterStateChanged(self, value):
        self.state_value_str = self._convert_state_to_str(value)
        self.emit("shutterStateChanged", (self.state_value_str,))

    def _convert_state_to_str(self, state):
        if isinstance(state, float):
            state = int(state)
        state_str = self.shutterState[str(state)]
        return state_str

    def readShutterState(self):
        state = self.shutter_channel.getValue()
        return self._convert_state_to_str(state)

    def getShutterState(self):
        return self.state_value_str

    def openShutter(self):
        # Try getting open command configured in xml
        # If command is not defined then try writing the channel
        if self.open_cmd is not None:
            self.open_cmd()
        else:
            self.shutter_channel.setValue(0)

    def closeShutter(self):
        # Try getting close command configured in xml
        # If command is not defined try writing the channel
        if self.close_cmd is not None:
            self.close_cmd()
        else:
            self.shutter_channel.setValue(1)

#
# def test():
#     hwr = HWR.getHardwareRepository()
#     hwr.connect()
#
#     shut = hwr.getHardwareObject("/fastshutter")
#
#     print(("Shutter State is: ", shut.readShutterState()))
#
#
# if __name__ == "__main__":
#     test()

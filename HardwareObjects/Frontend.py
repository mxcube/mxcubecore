"""Front End Tango Hardware Object
Example XML:
<device class = "Frontend">
  <username>label for users</username>
  <tangoname>orion:10000/fe/id(or d)/xx</tangoname>
  <command type="tango" name="Open">Automatic</command>
  <command type="tango" name="Manual">Manual</command>
  <command type="tango" name="Close">Close</command>
  <channel type="tango" name="State" polling="2000">State</channel>
  <channel type="tango" name="AutoModeTime" polling="2000">Auto_Mode_Time</channel>
</device>
"""

from HardwareRepository import BaseHardwareObjects
import logging
import math


class Frontend(BaseHardwareObjects.Device):
    shutterState = {
        0: "on",
        1: "off",
        2: "closed",
        3: "opened",
        4: "insert",
        5: "extract",
        6: "moving",
        7: "standby",
        8: "fault",
        9: "init",
        10: "running",
        11: "alarm",
        12: "disabled",
        13: "unknown",
        -1: "fault",
    }

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

        self.shutterStateValue = 13
        self.automaticModeTimeLeft = None
        self.undulatorGaps = {}

    def init(self):
        try:
            chanState = self.getChannelObject("State")
            chanState.connectSignal("update", self.valueChanged)
            self.setIsReady(True)
        except KeyError:
            logging.getLogger().warning("%s: cannot read current", self.name())

    def valueChanged(self, value):
        #
        # emit signal
        #
        self.shutterStateValue = value
        self.automaticModeTimeLeft = self.getChannelObject("AutoModeTime").getValue()
        self.emit(
            "shutterStateChanged",
            (self.shutterState[self.shutterStateValue], self.automaticModeTimeLeft),
        )

    def getShutterState(self):
        return self.shutterState[self.shutterStateValue]

    def getAutomaticModeTimeLeft(self):
        return self.automaticModeTimeLeft

    def openShutter(self):
        self.getCommandObject("Open")()

    def manualShutter(self):
        self.getCommandObject("Manual")()

    def closeShutter(self):
        self.getCommandObject("Close")()

    def getUndulatorGaps(self):
        if len(self.undulatorGaps) == 0:
            tangoname = self.getChannelObject("State").deviceName.replace("fe", "id")

            self.addChannel(
                {"type": "tango", "name": "MovableNames", "tangoname": tangoname},
                "MovableNames",
            )

            movable_names = self.getChannelObject("MovableNames").getValue()

            for name in movable_names:
                if "GAP" in name:
                    key = name + "_Position"
                    self.undulatorGaps[key] = -1
                    self.addChannel(
                        {"type": "tango", "name": key, "tangoname": tangoname}, key
                    )

        for key in list(self.undulatorGaps.keys()):
            gap = self.getChannelObject(key).getValue()
            if gap is None or math.isnan(gap):
                gap = -1
            self.undulatorGaps[key] = gap

        return self.undulatorGaps

    def getUndulatorGap(self, name):
        undulator_gaps = self.getUndulatorGaps()
        for key in list(undulator_gaps.keys()):
            if name.lower() in key.lower():
                return undulator_gaps[key]

    def moveUndulatorGaps(self, gaps):
        curr_gaps = self.getUndulatorGaps()
        for key in list(curr_gaps.keys()):
            for nkey in list(gaps.keys()):
                if nkey.lower() in key.lower():
                    self.getChannelObject(key).setValue(gaps[nkey])

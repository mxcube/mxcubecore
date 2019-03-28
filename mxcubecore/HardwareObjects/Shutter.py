from HardwareRepository.HardwareObjects import TacoDevice
import logging


class Shutter(TacoDevice.TacoDevice):
    shutterState = {
        0: "unknown",
        3: "closed",
        4: "opened",
        9: "moving",
        17: "automatic",
        23: "fault",
        46: "disabled",
        -1: "error",
    }

    def __init__(self, name):
        TacoDevice.TacoDevice.__init__(self, name)

        self.shutterStateValue = 0

    def init(self):
        if self.device.imported:
            self.setPollCommand("DevState")

            self.setIsReady(True)

    def valueChanged(self, deviceName, value):
        #
        # emit signal
        #
        self.shutterStateValue = value
        self.emit(
            "shutterStateChanged", (Shutter.shutterState[self.shutterStateValue],)
        )

    def getShutterState(self):
        return Shutter.shutterState[self.shutterStateValue]

    def isShutterOk(self):
        return not self.getShutterState() in (
            "unknown",
            "moving",
            "fault",
            "disabled",
            "error",
        )

    def openShutter(self):
        if self.isReady() and self.isShutterOk():
            self.device.DevOpen()
        else:
            logging.getLogger("HWR").error(
                "%s: cannot open shutter (%s)", self.name(), self.getShutterState()
            )

    def closeShutter(self):
        if self.isReady() and self.isShutterOk():
            self.device.DevClose()
        else:
            logging.getLogger("HWR").error(
                "%s: cannot close shutter (%s)", self.name(), self.getShutterState()
            )

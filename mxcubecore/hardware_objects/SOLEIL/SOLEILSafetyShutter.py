from mxcubecore.BaseHardwareObjects import HardwareObject

import logging


class SOLEILSafetyShutter(HardwareObject):
    def __init__(self, name):

        HardwareObject.__init__(self, name)

        self.pss = None
        self.shutter = None

    def init(self):
        try:
            self.shutter = self.get_object_by_role("shutter")
            self.pss = self.get_object_by_role("pss")
            logging.debug("shutter is " + str(self.shutter))
            logging.debug("pss is " + str(self.pss))
            self.connect(self.shutter, "shutterStateChanged", self.shutterStateChanged)
            self.connect(self.pss, "wagoStateChanged", self.shutterStateChanged)
        except Exception:
            import traceback

            print(traceback.print_exc())
            logging.debug(traceback.format_exc())
            logging.getLogger().warning("pss device not configured")

    def getShutterState(self):
        logging.debug(" shutter is %s " % str(self.shutter))

        if self.pss.getWagoState() != "ready":
            return "disabled"

        if self.shutter is None:
            return "unknown"
        return self.shutter.getShutterState()

    def shutterStateChanged(self, value):
        if self.shutter is None:
            return
        #
        # emit signal
        #
        self.shutterStateValue = value  # str(value)
        self.emit("shutterStateChanged", (self.getShutterState(),))
        self.emit("stateChanged", (self.getShutterState(),))

    def openShutter(self):
        if self.shutter is None:
            return
        if self.pss is None:
            logging.error("no pss device for safety shutter. check configuration")
            return

        if self.pss.getWagoState() == "ready":
            self.shutter.openShutter()
            logging.info("Opening shutter ok")
        else:
            logging.warning("cannot open safety shutter. Check interlock")

    def closeShutter(self):
        if self.shutter is None:
            return
        self.shutter.closeShutter()

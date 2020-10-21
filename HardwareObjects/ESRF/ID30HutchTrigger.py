from HardwareRepository import BaseHardwareObjects
import logging
import PyTango.gevent
import gevent
import time
import sys


class ID30HutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)

    def _do_polling(self):
        while True:
            try:
                self.poll()
            except Exception:
                sys.excepthook(*sys.exc_info())
            time.sleep(self.getProperty("interval") / 1000.0 or 1)

    def init(self):
        try:
            self.device = PyTango.gevent.DeviceProxy(self.getProperty("tangoname"))
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None
            self.device.imported = False
        else:
            self.device.imported = True

        self.pollingTask = None
        self.initialized = False
        self.__oldValue = None
        self.card = None
        self.channel = None

        PSSinfo = self.getProperty("pss")
        try:
            self.card, self.channel = map(int, PSSinfo.split("/"))
        except Exception:
            logging.getLogger().error("%s: cannot find PSS number", self.name())
            return

        if self.device is not None:
            self.pollingTask = gevent.spawn(self._do_polling)

        self.connected()

    def hutchIsOpened(self):
        return self.hutch_opened

    def isConnected(self):
        return True

    def connected(self):
        self.emit("connected")

    def disconnected(self):
        self.emit("disconnected")

    def abort(self):
        pass

    def macro(self, entering_hutch, old={"dtox": None, "aperture": None}):
        logging.info(
            "%s: %s hutch", self.name(), "entering" if entering_hutch else "leaving"
        )
        eh_controller = self.getObjectByRole("eh_controller")
        if not entering_hutch:
            if old["dtox"] is not None:
                eh_controller.DtoX.set_value(old["dtox"], wait=False)
            if self.getObjectByRole("aperture") and old["aperture"] is not None:
                self.getObjectByRole("aperture").moveToPosition(old["aperture"])
            self.getObjectByRole("beamstop").moveToPosition("in")
            eh_controller.DtoX.wait_move()
        else:
            old["dtox"] = eh_controller.DtoX.position()
            if self.getObjectByRole("aperture"):
                old["aperture"] = self.getObjectByRole("aperture").get_value()
            eh_controller.DtoX.set_value(700, wait=False)
            if self.getObjectByRole("aperture"):
                self.getObjectByRole("aperture").moveToPosition("Outbeam")
            self.getObjectByRole("beamstop").moveToPosition("out")
            eh_controller.detcover.set_in()
            eh_controller.DtoX.wait_move()

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
        self.hutch_opened = 1 - value
        self.initialized = True

import logging
import PyTango.gevent
import gevent
import time
import sys
from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR


class ID29HutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)

    def _do_polling(self):
        while True:
            try:
                self.poll()
            except Exception:
                sys.excepthook(*sys.exc_info())
            time.sleep(self.get_property("interval") / 1000.0 or 1)

    def init(self):
        try:
            self.device = PyTango.gevent.DeviceProxy(self.get_property("tangoname"))
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.device = None

        self.pollingTask = None
        self.initialized = False
        self.__oldValue = None
        self.card = None
        self.channel = None

        PSSinfo = self.get_property("pss")
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

    def is_connected(self):
        return True

    def connected(self):
        self.emit("connected")

    def disconnected(self):
        self.emit("disconnected")

    def abort(self):
        pass

    def macro(self, entering_hutch, old={"dtox": None}):
        logging.info(
            "%s: %s hutch", self.id, "entering" if entering_hutch else "leaving"
        )
        dtox = HWR.beamline.detector.distance
        if not entering_hutch:
            if old["dtox"] is not None:
                dtox.set_value(old["dtox"])
            self.get_command_object("macro")(0)
        else:
            old["dtox"] = dtox.get_value()
            self.get_command_object("macro")(1)
            dtox.set_value(700)
        dtox.waitEndOfMove()

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

        self.value_changed(value)

    def value_changed(self, value, *args):
        if value == 0:
            if self.initialized:
                self.emit("hutchTrigger", (1,))
        elif value == 1 and self.initialized:
            self.emit("hutchTrigger", (0,))

        self.hutch_opened = 1 - value
        self.initialized = True

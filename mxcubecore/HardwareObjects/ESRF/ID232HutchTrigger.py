import logging
import PyTango.gevent
import gevent
import time
import sys
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import HardwareRepository as HWR

"""
Read the state of the hutch from the PSS device server and take actions
when enter (1) or interlock (0) the hutch.
0 = The hutch has been interlocked and the sample environment should be made
     ready for data collection. The actions are extract the detector cover,
     move the detector to its previous position, set the MD2 to Centring.
1 = The interlock is cleared and the user is entering the hutch to change
      the sample(s). The actions are insert the detector cover, move the
      detecto to a safe position, set MD2 to sample Transfer.
"""


class ID232HutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)
        self._enabled = True

    def _do_polling(self):
        while True:
            try:
                self.poll()
            except BaseException:
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

        try:
            self.flex_device = PyTango.gevent.DeviceProxy(
                self.get_property("flex_tangoname")
            )
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )
            self.flex_device = None

        self.pollingTask = None
        self.initialized = False
        self.__oldValue = None
        self.card = None
        self.channel = None

        PSSinfo = self.get_property("pss")
        try:
            self.card, self.channel = map(int, PSSinfo.split("/"))
        except BaseException:
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

    def macro(self, entering_hutch, old={"dtox": None}):
        logging.info(
            "%s: %s hutch", self.name(), "entering" if entering_hutch else "leaving"
        )
        dtox = HWR.beamline.detector.distance
        udiff_ctrl = self.get_object_by_role("predefined")
        ctrl_obj = self.get_object_by_role("controller")
        if not entering_hutch:
            if old["dtox"] is not None:
                print("Moving %s to %g" % (dtox.name(), old["dtox"]))
                dtox.set_value(old["dtox"])
            self.flex_device.eval("flex.user_port(0)")
            self.flex_device.eval("flex.robot_port(1)")
            udiff_ctrl.moveToPhase(phase="Centring", wait=True)
        else:
            old["dtox"] = dtox.get_value()
            ctrl_obj.detcover.set_in()
            self.flex_device.eval("flex.robot_port(0)")
            dtox.set_value(815)
            udiff_ctrl.moveToPhase(phase="Transfer", wait=True)

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

        if self._enabled:
            self.macro(self.hutch_opened)

    def get_actuator_state(self):
        if self._enabled:
            return "ENABLED"
        else:
            return "DISABLED"

    def actuatorIn(self):
        self._enabled = True

    def actuatorOut(self):
        self._enabled = False

import logging
import sys

import gevent
import PyTango.gevent

from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR

"""
Read the state of the hutch from the PSS device server and take actions
when enter (1) or interlock (0) the hutch.
0 = The hutch has been interlocked and the sample environment should be made
     ready for either loading a sample or a data collection.
1 = The interlock is cleared and the user is entering the hutch. The equipment
    is placed in safe position.
Example xml file:
<object class="ESRF.BlissHutchTrigger">
  <username>Hutchtrigger</username>
  <pss_tangoname>orion:10000/exp/id29-cr1/sl0</pss_tangoname>
  <pss_card_ch>7/1</pss_card_ch>
  <polling_interval>500</polling_interval>
  <object href="/bliss" role="controller"/>
  <object href="/sample_changer", role="sample_changer"/>
</object>
"""


class BlissHutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)
        self._enabled = True

    def _do_polling(self):
        while True:
            try:
                self.poll()
            except Exception:
                sys.excepthook(*sys.exc_info())
            gevent.sleep(self.get_property("polling_interval") / 1000.0 or 1)

    def init(self):
        try:
            self.device = PyTango.gevent.DeviceProxy(self.get_property("pss_tangoname"))
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

        PSSinfo = self.get_property("pss_card_ch")
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

    def macro(self, entering_hutch, **kwargs):
        logging.info(
            "%s: %s hutch", self.name(), "entering" if entering_hutch else "leaving"
        )
        ctrl_obj = self.get_object_by_role("controller")
        ctrl_obj.hutch_actions(entering_hutch, hutch_trigger=True, **kwargs)

        # open the flexHCD ports
        sample_changer = HWR.beamline.sample_changer
        if sample_changer:
            if entering_hutch:
                sample_changer.prepare_hutch(robot_port=0)
            else:
                sample_changer.prepare_hutch(user_port=0, robot_port=1)

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

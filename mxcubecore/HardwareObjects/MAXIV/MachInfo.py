"""
[Name] MachInfoMockup

[Description]
MachInfo hardware objects are used to obtain information from the accelerator
control system.

This is a mockup hardware object, it simulates the behaviour of an accelerator
information by :

    - produces a current value that varies with time
    - simulates a control room message that changes with some condition
      ()
    - simulates

[Emited signals]
machInfoChanged
   pars:  values (dict)

   mandatory fields:
     values['current']  type: str; desc: synchrotron radiation current in milli-amps
     values['message']  type: str; desc: message from control room
     values['attention'] type: boolean; desc: False (if no special attention is required)
                                            True (if attention should be raised to the user)

   optional fields:
      any number of optional fields can be sent over with this signal by adding them in the
      values dictionary

      for example:
         values['lifetime']
         values['topup_remaining']
"""

import logging
import gevent
import time
import PyTango
from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class MachInfo(HardwareObject):
    default_current = 0
    default_lifetime = 0
    default_message = ""
    default_topup_remaining = 0

    def __init__(self, *args):
        Equipment.__init__(self, *args)
        default_current = 0
        default_lifetime = 0
        default_message = ""
        default_topup_remaining = 0
        self.current = self.default_current
        self.lifetime = self.default_lifetime
        self.message = self.default_message

        self.mach_info_channel = None
        self.mach_curr_channel = None

    def init(self):
        try:
            # self.mach_info_channel =  self.get_channel_object("mach_info")
            channel = self.get_property("mach_info")
            self.mach_info_channel = PyTango.DeviceProxy(channel)
            self.message = self.mach_info_channel.OperatorMessage
            self.message += "\n" + self.mach_info_channel.R3NextInjection
        except Exception as ex:
            logging.getLogger("HWR").warning("Error initializing machine info channel")

        try:
            # self.curr_info_channel =  self.get_channel_object("curr_info")
            channel_current = self.get_property("current")
            self.curr_info_channel = PyTango.DeviceProxy(channel_current)
            # why twice??
            # why hwr channel does not work?? why??
            if self.curr_info_channel is None:
                self.curr_info_channel = PyTango.DeviceProxy(channel_current)
                curr = self.curr_info_channel.Current
            if curr < 0:
                self.current = 0.00
            else:
                self.current = "{:.2f}".format(curr * 1000)
            self.lifetime = float(
                "{:.2f}".format(self.curr_info_channel.Lifetime / 3600)
            )
        except Exception as ex:
            logging.getLogger("HWR").warning("Error initializing current info channel")

        self._run()

    def _run(self):
        gevent.spawn(self._update_me)

    def _update_me(self):
        self.t0 = time.time()

        while True:
            gevent.sleep(2)
            self.message = self.mach_info_channel.OperatorMessage
            self.message += "\n" + self.mach_info_channel.R3NextInjection
            curr = self.curr_info_channel.Current
            if curr < 0:
                self.current = 0.00
            else:
                self.current = "{:.2f}".format(curr * 1000)

            self.lifetime = float(
                "{:.2f}".format(self.curr_info_channel.Lifetime / 3600)
            )

            self.attention = False
            values = dict()
            values["current"] = self.current
            values["message"] = self.message
            values["lifetime"] = self.lifetime
            values["attention"] = self.attention
            self.emit("machInfoChanged", values)
            self.emit("valueChanged", values)

    def get_current(self):
        return self.current

    def getLifeTime(self):
        return self.lifetime

    def getTopUpRemaining(self):
        return self.topup_remaining

    def getMessage(self):
        return self.message


def test():
    import sys

    hwr = HWR.get_hardware_repository()
    hwr.connect()

    conn = hwr.get_hardware_object(sys.argv[1])

    print("Machine current: ", conn.get_current())
    print("Life time: ", conn.getLifeTime())
    print("TopUp remaining: ", conn.getTopUpRemaining())
    print("Message: ", conn.getMessage())

    while True:
        gevent.wait(timeout=0.1)


if __name__ == "__main__":
    test()

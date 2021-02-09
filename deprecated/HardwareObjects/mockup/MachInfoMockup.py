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

import gevent
import time

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import Equipment


class MachInfoMockup(Equipment):
    default_current = 200  # milliamps
    default_lifetime = 45  # hours Lifetime
    default_message = "Beam Delivered"
    default_topup_remaining = 70  # seconds

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.current = self.default_current
        self.lifetime = self.default_lifetime
        self.message = self.default_message
        self.topup_remaining = self.default_topup_remaining

    def init(self):
        self._run()

    def _run(self):
        gevent.spawn(self._update_me)

    def _update_me(self):
        self.t0 = time.time()

        while True:
            gevent.sleep(5)
            elapsed = time.time() - self.t0
            self.topup_remaining = abs((self.default_topup_remaining - elapsed) % 300)
            if self.topup_remaining < 60:
                self.message = "ATTENTION: topup in %3d secs" % int(
                    self.topup_remaining
                )
                self.attention = True
            else:
                self.message = self.default_message
                self.attention = False
            self.current = "%3.2f mA" % (
                self.default_current - (3 - self.topup_remaining / 100.0) * 5
            )
            values = dict()
            values["current"] = self.current
            values["message"] = self.message
            values["lifetime"] = "%3.2f hours" % self.lifetime
            values["topup_remaining"] = "%3.0f secs" % self.topup_remaining
            values["attention"] = self.attention

            self.emit("machInfoChanged", values)

    def get_current(self):
        return self.current

    def getLifeTime(self):
        return self.lifetime

    # def getTopUpRemaining(self):
    #     return self.topup_remaining

    def getMessage(self):
        return self.message


def test():
    import sys

    hwr = HWR.get_hardware_repository()
    hwr.connect()

    conn = hwr.get_hardware_object(sys.argv[1])

    print(("Machine current: ", conn.get_current()))
    print(("Life time: ", conn.getLifeTime()))
    print(("TopUp remaining: ", conn.getTopUpRemaining()))
    print(("Message: ", conn.getMessage()))

    while True:
        gevent.wait(timeout=0.1)


if __name__ == "__main__":
    test()

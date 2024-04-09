"""
[Name] MachineInfoMockup

[Description]
MachineInfo hardware objects are used to obtain information from the accelerator
control system.

This is a mockup hardware object, it simulates the behaviour of an accelerator
information by :

    - produces a current value that varies with time
    - simulates a control room message that changes with some condition

[Emitted signals]
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

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)


class MachineInfoMockup(AbstractMachineInfo):
    default_current = 200  # milliamps
    default_message = "Beam Delivered"
    default_lifetime = 45  # hours Lifetime
    default_topup_remaining = 70  # seconds

    def __init__(self, *args):
        AbstractMachineInfo.__init__(self, *args)

    def init(self):
        """Initialise some parameters and update routine."""
        self._current = self.default_current
        self._message = self.default_message
        self._lifetime = self.default_lifetime
        self._topup_remaining = self.default_topup_remaining
        self._run()

    def _run(self):
        """Spawn update routine."""
        gevent.spawn(self._update_me)

    def _update_me(self):
        self.t0 = time.time()

        while True:
            gevent.sleep(5)
            elapsed = time.time() - self.t0
            self._topup_remaining = abs((self.default_topup_remaining - elapsed) % 300)
            if self._topup_remaining < 60:
                self._message = "ATTENTION: topup in %3d secs" % int(
                    self._topup_remaining
                )
                self.attention = True
            else:
                self._message = self.default_message
                self.attention = False

            self._current = "%3.2f" % (
                self.default_current - (3 - self._topup_remaining / 100.0) * 5
            )

            values = dict()
            values["current"] = self._current
            values["message"] = self._message
            values["lifetime"] = self._lifetime
            values["topup_remaining"] = self._topup_remaining
            values["attention"] = self.attention
            self._mach_info_dict = values

            self.emit("valueChanged", values)

    def get_current(self) -> float:
        """Override method."""
        return self._current

    def get_lifetime(self) -> float:
        """Override method."""
        return self._lifetime

    def get_topup_remaining(self) -> float:
        """Override method."""
        return self._topup_remaining

    def get_message(self) -> str:
        """Override method."""
        return self._message


def test():
    import sys

    hwr = HWR.get_hardware_repository()
    hwr.connect()

    conn = hwr.get_hardware_object(sys.argv[1])

    print(("Machine current: ", conn.get_current()))
    print(("Life time: ", conn.get_lifetime()))
    print(("TopUp remaining: ", conn.get_topup_remaining()))
    print(("Message: ", conn.get_message()))
    print(("Values: ", conn.get_mach_info_dict()))

    while True:
        gevent.wait(timeout=0.1)


if __name__ == "__main__":
    test()

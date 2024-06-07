"""
[Name] MachineInfoMockup

[Description]
MachineInfo hardware objects are used to obtain information from the
accelerator control system.

This is a mockup hardware object, it simulates the behaviour of an accelerator
information by :

    - produces a current value that varies with time
    - simulates a control room message that changes with some condition
      ()
    - simulates

[Emitted signals]
valueChanged
   pars:  values (dict)

   mandatory fields:
     values['current']  type: str; desc: synchrotron radiation current in milli-amps
     values['message']  type: str; desc: message from control room
     values['attention'] type: boolean; desc: False (no attention required)
                                            True (attention raised to the user)

   optional fields:
      any number of optional fields can be sent over with this signal by
      adding them in the values dictionary

      for example:
         values['lifetime']
         values['topup_remaining']
"""
import time

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo


class P11MachineInfo(AbstractMachineInfo):
    """Simulates the behaviour of an accelerator information"""

    default_current = 100  # [mA]
    default_message = "Beam Delivered"
    default_lifetime = 45  # hours Lifetime
    default_topup_remaining = 70  # [s]

    def init(self):
        """Initialise some parameters and update routine."""
        super().init()
        self._current = self.default_current
        self._message = self.default_message
        self._lifetime = self.default_lifetime
        self._topup_remaining = self.default_topup_remaining
        self._run()

    def _run(self):
        """Spawn update routine."""
        gevent.spawn(self._update_me)

    def _update_me(self):
        """Simulate change of different parameters"""
        self.t0 = time.time()

        while True:
            gevent.sleep(5)
            elapsed = time.time() - self.t0
            self._topup_remaining = abs((self.default_topup_remaining - elapsed) % 300)
            if self._topup_remaining < 60:
                self._message = f"ATTENTION: topup in {self._topup_remaining} s"
                self.attention = True
            else:
                self._message = self.default_message
                self.attention = False

            self._current = f"{(self.default_current - (3 - self._topup_remaining / 100.0) * 5):3.2f}"

            values = {}
            values["message"] = self._message
            values["topup_remaining"] = self._topup_remaining
            values["attention"] = self.attention

            # current and lifetime should be configured in the xml file
            values.update(self.get_value())
            self.update_value(values)

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
    """Test routine"""
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

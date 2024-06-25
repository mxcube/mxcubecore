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
from PyTango import DeviceProxy


class P11MachineInfo(AbstractMachineInfo):
    """Simulates the behaviour of an accelerator information"""

    default_current = 100.0  # [mA]
    default_message = "Machine message is not updated"
    default_lifetime = 1.85  # hours Lifetime
    default_maschine_energy = 6.08  # GeV

    def init(self):
        """Initialise some parameters and update routine."""
        super().init()

        self.devPathGlobal = "PETRA/globals/keyword"
        self.devGlobal = DeviceProxy(self.devPathGlobal)

        self._current = self.default_current
        self._message = self.default_message
        self._lifetime = self.default_lifetime
        self._maschine_energy = self.default_maschine_energy

        self._run()

    def _run(self):
        """Spawn update routine."""
        gevent.spawn(self._update_me)

    def _update_me(self):
        self._current = self.devGlobal.read_attribute("BeamCurrent").value
        self._message = self.devGlobal.read_attribute("MessageText").value
        self._lifetime = self.devGlobal.read_attribute("BeamLifetime").value
        self._maschine_energy = self.devGlobal.read_attribute("Energy").value

    def get_current(self) -> float:
        """Override method."""
        return self._current

    def get_lifetime(self) -> float:
        """Override method."""
        return self._lifetime

    def get_message(self) -> str:
        """Override method."""
        return self._message

    def get_maschine_energy(self) -> float:
        """Override method."""
        return self._maschine_energy


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

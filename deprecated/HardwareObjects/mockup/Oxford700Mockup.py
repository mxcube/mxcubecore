# pylint: skip-file

from mx3core.BaseHardwareObjects import HardwareObject
from mx3core import HardwareRepository as HWR
import gevent
import sys
import random

CRYO_STATUS = ["OFF", "SATURATED", "READY", "WARNING", "FROZEN", "UNKNOWN"]
PHASE_ACTION = {
    "RAMP": "ramp",
    "COOL": "set",
    "HOLD": "hold",
    "PLAT": "plat",
    "PURGE": "purge",
    "END": "end",
}


class Oxford700Mockup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.n2level = None
        self.temp = None
        self.temp_error = None
        self.ii = 0

    def _do_polling(self):
        while True:
            try:
                self.value_changed()
            except Exception:
                sys.excepthook(*sys.exc_info())
            gevent.sleep(self.interval)

    def init(self):
        controller = self.get_property("controller")
        self.interval = self.get_property("interval") or 10
        cryostat = self.get_property("cryostat")
        self.ctrl = OxfordDummy()
        if self.ctrl is not None:
            gevent.spawn(self._do_polling)

    def value_changed(self):
        self.emit("temperatureChanged", (self.get_temperature(),))
        self.emit("stateChanged", (self.get_state(),))

    def get_temperature(self):
        self.temp = self.ctrl.get_temperature()
        return self.temp

    def start_action(self, phase="RAMP", target=None, rate=None):
        if phase in PHASE_ACTION:
            action = getattr(self.ctrl, PHASE_ACTION[phase])
            if rate:
                action(target, rate)
            elif target:
                action(target)
            else:
                action()

    """
    def update_params(self):
        self.ctrl.update_cmd()
    """

    def stop_action(self, phase="RAMP"):
        if phase in PHASE_ACTION:
            action = PHASE_ACTION[phase]
            print(action)

    def get_state(self):
        STATE = ["UNKNOWN", "IDLE", "RUNNING", "HOLD"]
        self.cryo_state = "HOLD"  # STATE[random.randint(0,2)]
        return self.cryo_state

    def get_params(self):
        if self.ii % 2:
            state = "Ramp"
        else:
            state = "Hold"
        self.ii += 1
        return [98.34, 2.5, state.upper(), state]


class OxfordDummy:
    def __init__(self):
        self.temp = None

    def get_temperature(self):
        self.temp = random.uniform(0, 100)
        print((self.temp))
        return self.temp

    def ramp(self, temp, rate):
        print(("ramp ", temp))
        print(rate)

    def set(self, temp):
        print(("set ", temp))

    def hold(self):
        print("hold called")

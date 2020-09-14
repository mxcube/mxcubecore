from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR
import gevent
import sys

CRYO_STATUS = ["OFF", "SATURATED", "READY", "WARNING", "FROZEN", "UNKNOWN"]
PHASE_ACTION = {
    "RAMP": "ramp",
    "COOL": "set",
    "HOLD": "hold",
    "PLAT": "plat",
    "PURGE": "purge",
    "END": "end",
}


class Oxford700(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.temp = None
        self.temp_error = None

    def _do_polling(self):
        while True:
            try:
                self.value_changed()
            except BaseException:
                sys.excepthook(*sys.exc_info())
            gevent.sleep(self.interval)

    def init(self):
        controller = HWR.getHardwareRepository().get_hardware_object(
            self.get_property("controller")
        )
        cryostat = self.get_property("cryostat")
        self.interval = self.get_property("interval") or 10
        self.ctrl = getattr(controller, cryostat)
        if self.ctrl is not None:
            # self.get_params()
            gevent.spawn(self._do_polling)

    def value_changed(self):
        self.emit("temperatureChanged", (self.get_temperature(),))
        self.emit("valueChanged", (self.get_temperature(),))
        self.emit("stateChanged", (self.get_state(),))

    def get_temperature(self):
        return self.ctrl.read()

    def get_value(self):
        return self.get_temperature()

    def rampstate(self):
        return self.ctrl.rampstate()

    def start_action(self, phase="RAMP", target=None, rate=None):
        if phase in PHASE_ACTION:
            action = getattr(self.ctrl, PHASE_ACTION[phase])
            if rate:
                action(target, rate=rate)
            elif target:
                action(target)
            else:
                action()

    def update_params(self):
        self.ctrl.controller._oxford._update_cmd()

    def stop_action(self, phase="HOLD"):
        if phase in PHASE_ACTION:
            getattr(self.ctrl, PHASE_ACTION[phase])

    def pause(self, execute=True):
        self.ctrl.pause(execute)

    def get_state(self):
        # _, _, _, run_mode = self.get_params()
        state = self.ctrl.state()
        if isinstance(state, list):
            run_mode = state[0]
        else:
            run_mode = state
        try:
            self.cryo_state = run_mode.upper()
        except TypeError:
            self.cryo_state = "UNKNOWN"
        return self.cryo_state

    def get_static_parameters(self):
        return ["oxford", "K", "hour"]

    def get_params(self):
        self.update_params()
        target = self.ctrl.controller._oxford.statusPacket.target_temp
        rate = self.ctrl.controller._oxford.statusPacket.ramp_rate
        phase = self.ctrl.controller._oxford.statusPacket.phase
        run_mode = self.ctrl.controller._oxford.statusPacket.run_mode
        self.temp = self.ctrl.controller._oxford.statusPacket.gas_temp
        return [target, rate, phase.upper(), run_mode]

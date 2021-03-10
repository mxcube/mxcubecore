from mxcubecore.BaseHardwareObjects import Device
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
import time
import gevent


class RobodiffLight(Device, AbstractMotor):
    states = {0: "out", 1: "in"}
    READ_CMD, READ_OUT = (0, 1)
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        controller = self.get_object_by_role("controller")

        self._state = None
        self.username = self.name()
        self.wago_controller = getattr(controller, self.wago)
        self.command_key = self.get_property("cmd")
        self.in_key = self.get_property("is_in")
        self.out_key = self.get_property("is_out")
        self.light_level = self.get_property("level")
        self.wago_polling = gevent.spawn(self._wago_polling, self.command_key)
        self.set_is_ready(True)

    def _wago_polling(self, key):
        while True:
            try:
                reading = int(self.wago_controller.get(key))
            except Exception:
                time.sleep(1)
                continue
            if self._state != reading:
                self._state = reading
                self.emit("wagoStateChanged", (self.getWagoState(),))
            time.sleep(1)

    def getWagoState(self):
        return RobodiffLight.states.get(self._state, "unknown")

    def wagoIn(self):
        with gevent.Timeout(5):
            self.wago_controller.set(self.command_key, 1)
            while self.wago_controller.get(self.in_key) == 0:
                time.sleep(0.5)

    def wagoOut(self):
        with gevent.Timeout(5):
            self.wago_controller.set(self.command_key, 0)
            while self.wago_controller.get(self.out_key) == 0:
                time.sleep(0.5)

    def get_value(self):
        return self.wago_controller.get(self.light_level)

    def get_limits(self):
        return (0, 10)

    def get_state(self):
        return RobodiffLight.READY

    def _set_value(self, value):
        self.wago_controller.set(self.light_level, value)

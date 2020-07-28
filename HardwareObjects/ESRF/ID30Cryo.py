from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import task
import time
import gevent


class ID30Cryo(Device):
    states = {0: "out", 1: "in"}

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
        self.wago_polling = self._wago_polling(self.command_key, wait=False)
        self.set_is_ready(True)

    @task
    def _wago_polling(self, key):
        while True:
            try:
                reading = int(self.wago_controller.get(key))
            except BaseException:
                time.sleep(1)
                continue
            if self._state != reading:
                self._state = reading
                self.emit("wagoStateChanged", (self.getWagoState(),))
                self.emit("actuatorStateChanged", (self.getWagoState(),))
            time.sleep(1)

    def getWagoState(self):
        return ID30Cryo.states.get(self._state, "unknown")

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

    def get_actuator_state(self):
        return self.getWagoState()

    def actuatorIn(self):
        return self.wagoIn()

    def actuatorOut(self):
        return self.wagoOut()

    def get_state(self):
        return ID30Cryo.READY

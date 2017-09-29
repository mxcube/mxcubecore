from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import *
import logging
import time
import gevent

class ID30Cryo(Device):
    states = {
      0:   "out",
      1:   "in",
    }

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        controller = self.getObjectByRole("controller")

        self._state = None
        self.username = self.name()
        self.wago_controller = getattr(controller, self.wago)
        self.command_key = self.getProperty("cmd")
        self.in_key = self.getProperty("is_in")
        self.out_key = self.getProperty("is_out")
        self.wago_polling = self._wago_polling(self.command_key,wait=False)
        self.setIsReady(True)
     
    @task 
    def _wago_polling(self, key):
        while True:
            try:
              reading = int(self.wago_controller.get(key))
            except:
              time.sleep(1)
              continue
            if self._state != reading:
                self._state = reading
                self.emit("wagoStateChanged", (self.getWagoState(), ))
                self.emit("actuatorStateChanged", (self.getWagoState(), ))
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

    def getActuatorState(self):
        return self.getWagoState()

    def actuatorIn(self):
        return self.wagoIn()

    def actuatorOut(self):
         return self.wagoOut()

    def getState(self):
        return ID30Cryo.READY

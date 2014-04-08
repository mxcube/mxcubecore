from HardwareRepository.BaseHardwareObjects import Device
import logging
import time
import gevent

class RobodiffLight(Device):
    states = {
      0:   "out",
      1:   "in",
    }
    READ_CMD, READ_OUT = (0,1)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        controller = self.getObjectByRole("controller")

	self._state = None
        self.wago_controller = getattr(controller, self.wago)
        self.command_key = self.getProperty("cmd")
        self.wago_polling = gevent.spawn(self._wago_polling, self.command_key)
        self.setIsReady(True)
      
    def _wago_polling(self, key):
        while True:
            reading = int(self.wago_controller.get(key))
            if self._state != reading:
                self._state = reading
                self.emit("wagoStateChanged", (self.getWagoState(), ))
            time.sleep(1)
 
    def getWagoState(self):
        return RobodiffLight.states.get(self._state, "unknown")

    def wagoIn(self):
        if self.isReady():
            self.wago_controller.set(self.command_key, 1)

    def wagoOut(self):
        if self.isReady():
            self.wago_controller.set(self.command_key, 0)

    def getPosition(self):
        return 0

    def getLimits(self):
        return (0, 10)

    def move(self, abs_pos):
        return 

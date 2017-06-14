from HardwareRepository.BaseHardwareObjects import Device
import logging
import time
import gevent

class ID30Light(Device):
    states = {
      0:   "out",
      1:   "in",
    }
    READ_CMD, READ_OUT = (0,1)
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)   

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        controller = self.getObjectByRole("controller")

        self.username = self.name()
        self.wago_controller = getattr(controller, self.wago)
        self.command_key = self.getProperty("cmd")
        self.in_key = self.getProperty("is_in")
        self.out_key = self.getProperty("is_out")
        self.light_level = self.getProperty("level")

        try:
            self._state = self.wago_controller.get(self.command_key)
        except:
            self._state = None
        #self.wago_polling = gevent.spawn(self._wago_polling, self.command_key)
        self.setIsReady(True)
      
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
        return ID30Light.states.get(self._state, "unknown")

    def getActuatorState(self):
         return self.getWagoState()    
  
    def wagoIn(self):
        with gevent.Timeout(5):
            self.wago_controller.set(self.command_key, 1)
            while self.wago_controller.get(self.in_key) == 0:
                time.sleep(0.5)
            self._state = self.wago_controller.get(self.in_key)
        self.emit("wagoStateChanged", (self.getWagoState(), ))
        self.emit("actuatorStateChanged", (self.getWagoState(), ))

    def actuatorIn(self):
        return self.wagoIn()

    def wagoOut(self):
        with gevent.Timeout(5):
            self.wago_controller.set(self.command_key, 0)
            while self.wago_controller.get(self.out_key) == 0:
                time.sleep(0.5)
            self._state = self.wago_controller.get(self.in_key)
        self.emit("wagoStateChanged", (self.getWagoState(), ))
        self.emit("actuatorStateChanged", (self.getWagoState(), ))

    def actuatorOut(self):
        return self.wagoOut()

    def getPosition(self):
        return self.wago_controller.get(self.light_level)

    def getLimits(self):
        return (0, 10)

    def getState(self):
        return ID30Light.READY

    def move(self, abs_pos):
        self.wago_controller.set(self.light_level, abs_pos)
        self.emit("positionChanged", abs_pos)

    def moveRelative(self, rel_pos):
        abs_pos = self.getPosition() + rel_pos
        self.move(abs_pos)

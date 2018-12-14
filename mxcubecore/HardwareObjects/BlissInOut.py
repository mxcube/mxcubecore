import logging
from HardwareRepository.BaseHardwareObjects import Device
from bliss.controllers.actuator_inout import *


class BlissInOut(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.actuatorState = "unknown"
        self.username = "unknown"
        # default timeout - 3 sec
        self.timeout = 3

    def init(self):
        self.username = self.getProperty("username")
        name = self.getProperty("name")
        self.actuator = getattr(self.getObjectByRole("controller"), name)

    def connectNotify(self, signal):
        if signal == "actuatorStateChanged":
            self.valueChanged()

    def valueChanged(self):
        self.actuatorState = self.actuator.state().lower()
        self.emit("actuatorStateChanged", (self.actuatorState,))

    def getActuatorState(self):
        if self.actuatorState == "unknown":
            self.connectNotify("actuatorStateChanged")

        logging.getLogger().info("%s state: %s" % (self.username, self.actuatorState))
        return self.actuatorState

    def actuatorIn(self):
        self.actuator.set_in()
        self.valueChanged()

    def actuatorOut(self):
        self.actuator.set_out()
        self.valueChanged()

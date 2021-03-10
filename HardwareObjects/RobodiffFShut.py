from mxcubecore.BaseHardwareObjects import Equipment


class RobodiffFShut(Equipment):
    def __init__(self, name):
        Equipment.__init__(self, name)

    def init(self):
        self.robodiff = self.get_object_by_role("robot")
        self.connect(self.robodiff.controller.fshut, "state", self.value_changed)
        self.actuatorState = "unknown"

    def connect_notify(self, signal):
        if signal == "actuatorStateChanged":
            self.get_actuator_state(read=True)

    def value_changed(self, value):
        if value == "CLOSED":
            self.actuatorState = "out"
        elif value == "OPENED":
            self.actuatorState = "in"
        else:
            self.actuatorState = "unknown"
        self.emit("actuatorStateChanged", (self.actuatorState,))
        self.emit("actuatorStateChanged", (self.actuatorState,))

    def getWagoState(self, *args):
        return self.get_actuator_state(self, *args)

    def get_actuator_state(self, read=False):
        if read:
            self.value_changed(self.robodiff.controller.fshut.state())
        return self.actuatorState

    def actuatorIn(self, wait=True, timeout=None):
        self.robodiff.controller.fshut.open()
        self.get_actuator_state(read=True)

    def wagoIn(self):
        return self.actuatorIn()

    def actuatorOut(self, wait=True, timeout=None):
        self.robodiff.controller.fshut.close()
        self.get_actuator_state(read=True)

    def wagoOut(self):
        return self.actuatorOut()

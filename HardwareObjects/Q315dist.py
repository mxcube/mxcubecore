from HardwareRepository import BaseHardwareObjects


class Q315dist(BaseHardwareObjects.Equipment):
    def _init(self):
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        return BaseHardwareObjects.Equipment._init(self)

    def init(self):
        self.detm = self.getDeviceByRole("detm")
        self.dtox = self.getDeviceByRole("detector_distance")

        self.connect(self.detm, "stateChanged", self.detmStateChanged)
        self.connect(self.dtox, "limitsChanged", self.dtoxLimitsChanged)
        self.connect(self.detm, "positionChanged", self.detmPositionChanged)

    def equipmentReady(self):
        self.emit("deviceReady")

    def equipmentNotReady(self):
        self.emit("deviceNotReady")

    def isValid(self):
        return (
            self.getDeviceByRole("detm") is not None
            and self.getDeviceByRole("detector_distance") is not None
        )

    def __getattr__(self, attr):
        """Delegation to underlying motors"""
        if not attr.startswith("__"):
            if attr in ("getPosition", "getDialPosition", "getState", "getLimits"):
                # logging.getLogger().info("calling detm %s ; ready ? %s", attr, self.detm.isReady())
                return getattr(self.detm, attr)
            else:
                # logging.getLogger().info("calling dtox %s", attr)
                return getattr(self.dtox, attr)
        else:
            raise AttributeError(attr)

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.detmStateChanged(self.detm.getState())
        elif signal == "positionChanged":
            self.detmPositionChanged(self.detm.getPosition())

    def detmStateChanged(self, state):
        if (state == self.detm.NOTINITIALIZED) or (state > self.detm.UNUSABLE):
            self.emit("stateChanged", (state,))
        else:
            self.detm.motorState = self.detm.READY
            self.detm.motorStateChanged(self.detm.motorState)

    def dtoxLimitsChanged(self, limits):
        self.emit("limitsChanged", (limits,))

    def detmPositionChanged(self, pos):
        self.emit("positionChanged", (pos,))

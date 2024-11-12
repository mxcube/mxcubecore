from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR


class Q315dist(BaseHardwareObjects.Equipment):
    def _init(self):
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        return BaseHardwareObjects.super()._init()

    def init(self):
        self.detm = self.get_deviceby_role("detm")

        self.connect(self.detm, "stateChanged", self.detmStateChanged)
        self.connect(
            HWR.beamline.detector.distance, "limitsChanged", self.dtoxLimitsChanged
        )
        self.connect(self.detm, "valueChanged", self.detmPositionChanged)

    def equipmentReady(self):
        self.emit("deviceReady")

    def equipmentNotReady(self):
        self.emit("deviceNotReady")

    def is_valid(self):
        return (
            self.get_deviceby_role("detm") is not None
            and self.get_deviceby_role("detector_distance") is not None
        )

    def __getattr__(self, attr):
        """Delegation to underlying motors"""
        if not attr.startswith("__"):
            if attr in ("get_value", "get_state", "get_limits"):
                # logging.getLogger().info("calling detm %s ; ready ? %s", attr, self.detm.is_ready())
                return getattr(self.detm, attr)
            else:
                # logging.getLogger().info("calling dtox %s", attr)
                return getattr(HWR.beamline.detector.distance, attr)
        else:
            raise AttributeError(attr)

    def connect_notify(self, signal):
        if signal == "stateChanged":
            self.detmStateChanged(self.detm.get_state())
        elif signal == "valueChanged":
            self.detmPositionChanged(self.detm.get_value())

    def detmStateChanged(self, state):
        if (state == self.detm.NOTINITIALIZED) or (state > self.detm.UNUSABLE):
            self.emit("stateChanged", (state,))
        else:
            self.detm.motorState = self.detm.READY
            self.detm.motorStateChanged(self.detm.motorState)

    def dtoxLimitsChanged(self, limits):
        self.emit("limitsChanged", (limits,))

    def detmPositionChanged(self, pos):
        self.emit("valueChanged", (pos,))

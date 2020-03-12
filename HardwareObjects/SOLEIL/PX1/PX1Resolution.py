import math
import logging
import time

from HardwareRepository.Command.Tango import DeviceProxy

from HardwareRepository.BaseHardwareObjects import Equipment

DETECTOR_DIAMETER = 424.0

NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT = (0, 1, 2, 3, 4, 5)


class PX1Resolution(Equipment):

    stateDict = {
        "UNKNOWN": 0,
        "ALARM": 1,
        "STANDBY": 2,
        "RUNNING": 4,
        "MOVING": 4,
        "FAULT": 1,
        "1": 1,
        "2": 2,
    }

    def _init(self):

        self.currentResolution = None
        self.currentDistance = None

        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        self.distance_chan = self.getChannelObject("distance")
        self.resolution_chan = self.getChannelObject("resolution")
        self.minimum_res_chan = self.getChannelObject("minimum_resolution")
        self.maximum_res_chan = self.getChannelObject("maximum_resolution")
        self.minimum_dist_chan = self.getChannelObject("minimum_distance")
        self.state_chan = self.getChannelObject("state")

        self.stop_command = self.get_command_object("stop")

        self.distance_chan.connectSignal("update", self.distanceChanged)
        self.resolution_chan.connectSignal("update", self.resolutionChanged)
        self.minimum_res_chan.connectSignal("update", self.minimumResolutionChanged)
        self.maximum_res_chan.connectSignal("update", self.maximumResolutionChanged)
        self.minimum_dist_chan.connectSignal("update", self.minimumDistanceChanged)
        self.state_chan.connectSignal("update", self.stateChanged)

        self.currentDistance = self.distance_chan.getValue()
        self.currentResolution = self.resolution_chan.getValue()

        return Equipment._init(self)

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.stateChanged()
        elif signal == "distanceChanged":
            self.distanceChanged()
        elif signal == "resolutionChanged":
            self.resolutionChanged()
        elif signal == "distanceLimitsChanged":
            self.minimumResolutionChanged()
        elif signal == "resolutionLimitsChanged":
            self.minimumResolutionChanged()

    def equipmentReady(self):
        self.emit("deviceReady")

    def equipmentNotReady(self):
        self.emit("deviceNotReady")

    def getState(self, value=None):
        if value is None:
            value = self.state_chan.getValue()
        state_str = str(value)
        # return self.stateDict[state_str]
        return state_str

    def get_value(self):
        if self.currentResolution is None:
            self.recalculateResolution()
        return self.currentResolution

    def getDistance(self):
        if self.currentResolution is None:
            self.recalculateResolution()
        return self.currentDistance

    def minimumResolutionChanged(self, value=None):
        self.emit("resolutionLimitsChanged", (self.get_limits(),))

    def maximumResolutionChanged(self, value=None):
        self.emit("resolutionLimitsChanged", (self.get_limits(),))

    def minimumDistanceChanged(self, value=None):
        self.emit("distanceLimitsChanged", (self.getDistanceLimits(),))

    def stateChanged(self, state=None):
        self.emit("stateChanged", (self.getState(state),))

    def distanceChanged(self, value=None):
        self.recalculateResolution()

    def resolutionChanged(self, value=None):
        self.recalculateResolution()

    def recalculateResolution(self):
        distance = self.distance_chan.getValue()
        resolution = self.resolution_chan.getValue()

        if resolution is None or distance is None:
            return

        if (self.currentResolution is not None) and abs(
            resolution - self.currentResolution
        ) > 0.001:
            self.currentResolution = resolution
            self.emit("resolutionChanged", (resolution,))

        if (self.currentDistance is not None) and abs(
            distance - self.currentDistance
        ) > 0.001:
            self.currentDistance = distance
            self.emit("distanceChanged", (distance,))

    def getDistanceLimits(self):

        chan_info = self.distance_chan.getInfo()

        high = float(chan_info.max_value)
        low = self.minimum_dist_chan.getValue()

        return [low, high]

    def get_limits(self):
        high = self.maximum_res_chan.getValue()
        low = self.minimum_res_chan.getValue()

        return (low, high)

    def moveResolution(self, res):
        self.resolution_chan.setValue(res)

    def moveDistance(self, dist):
        self.distance_chan.setValue(dist)

    def stop(self):
        try:
            self.stop_command()
        except BaseException:
            logging.getLogger("HWR").err(
                "%s: PX1Resolution.stop: error while trying to stop!", self.name()
            )

    def update_values(self):
        self.stateChanged()
        self.distanceChanged()
        self.resolutionChanged()
        self.minimumResolutionChanged()
        self.minimumResolutionChanged()

    move = moveResolution


def test_hwo(hwo):
    print("Distance [limits]", hwo.getDistance(), hwo.getDistanceLimits())
    print("Resolution [limits]", hwo.get_value(), hwo.get_limits())

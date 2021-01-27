import math
import logging
import time

from mxcubecore.Command.Tango import DeviceProxy

from mxcubecore.BaseHardwareObjects import Equipment

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

        self._nominal_value = None
        self.currentDistance = None

        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        self.distance_chan = self.get_channel_object("distance")
        self.resolution_chan = self.get_channel_object("resolution")
        self.minimum_res_chan = self.get_channel_object("minimum_resolution")
        self.maximum_res_chan = self.get_channel_object("maximum_resolution")
        self.minimum_dist_chan = self.get_channel_object("minimum_distance")
        self.state_chan = self.get_channel_object("state")

        self.stop_command = self.get_command_object("stop")

        self.distance_chan.connect_signal("update", self.distanceChanged)
        self.resolution_chan.connect_signal("update", self.resolutionChanged)
        self.minimum_res_chan.connect_signal("update", self.minimumResolutionChanged)
        self.maximum_res_chan.connect_signal("update", self.maximumResolutionChanged)
        self.minimum_dist_chan.connect_signal("update", self.minimumDistanceChanged)
        self.state_chan.connect_signal("update", self.stateChanged)

        self.currentDistance = self.distance_chan.get_value()
        self._nominal_value = self.resolution_chan.get_value()

        return Equipment._init(self)

    def connect_notify(self, signal):
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

    def get_state(self, value=None):
        if value is None:
            value = self.state_chan.get_value()
        state_str = str(value)
        # return self.stateDict[state_str]
        return state_str

    def get_value(self):
        if self._nominal_value is None:
            self.recalculateResolution()
        return self._nominal_value

    def getDistance(self):
        if self._nominal_value is None:
            self.recalculateResolution()
        return self.currentDistance

    def minimumResolutionChanged(self, value=None):
        self.emit("resolutionLimitsChanged", (self.get_limits(),))

    def maximumResolutionChanged(self, value=None):
        self.emit("resolutionLimitsChanged", (self.get_limits(),))

    def minimumDistanceChanged(self, value=None):
        self.emit("distanceLimitsChanged", (self.getDistanceLimits(),))

    def stateChanged(self, state=None):
        self.emit("stateChanged", (self.get_state(state),))

    def distanceChanged(self, value=None):
        self.recalculateResolution()

    def resolutionChanged(self, value=None):
        self.recalculateResolution()

    def recalculateResolution(self):
        distance = self.distance_chan.get_value()
        resolution = self.resolution_chan.get_value()

        if resolution is None or distance is None:
            return

        if (self._nominal_value is not None) and abs(
            resolution - self._nominal_value
        ) > 0.001:
            self._nominal_value = resolution
            self.emit("resolutionChanged", (resolution,))

        if (self.currentDistance is not None) and abs(
            distance - self.currentDistance
        ) > 0.001:
            self.currentDistance = distance
            self.emit("distanceChanged", (distance,))

    def getDistanceLimits(self):

        chan_info = self.distance_chan.getInfo()

        high = float(chan_info.max_value)
        low = self.minimum_dist_chan.get_value()

        return [low, high]

    def get_limits(self):
        high = self.maximum_res_chan.get_value()
        low = self.minimum_res_chan.get_value()

        return (low, high)

    def moveResolution(self, res):
        self.resolution_chan.set_value(res)

    def moveDistance(self, dist):
        self.distance_chan.set_value(dist)

    def stop(self):
        try:
            self.stop_command()
        except Exception:
            logging.getLogger("HWR").err(
                "%s: PX1Resolution.stop: error while trying to stop!", self.name()
            )

    def re_emit_values(self):
        self.stateChanged()
        self.distanceChanged()
        self.resolutionChanged()
        self.minimumResolutionChanged()
        self.minimumResolutionChanged()

    move = moveResolution


def test_hwo(hwo):
    print("Distance [limits]", hwo.getDistance(), hwo.getDistanceLimits())
    print("Resolution [limits]", hwo.get_value(), hwo.get_limits())

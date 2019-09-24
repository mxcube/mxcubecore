import logging
import math
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor
from HardwareRepository import HardwareRepository as HWR


class Resolution(AbstractMotor):
    def __init__(self, *args, **kwargs):
        AbstractMotor.__init__(self, name="Resolution")

        # self.get_value = self.getPosition
        self.valid = True
        self.det_width = None
        self.det_height = None
        self.detector_distance = None

    def init(self):
        self.currentResolution = None
        detector = HWR.beamline.detector
        self.detector_distance = self.getObjectByRole("detector_distance")

        if detector:
            self.det_width = float(detector.getProperty("width"))
            self.det_height = float(detector.getProperty("height"))
        else:
            self.valid = False
            logging.getLogger().exception("Cannot get detector properties")
            raise AttributeError("Cannot get detector properties")

        self.connect(
            self.detector_distance,
            "stateChanged",
            self.dtoxStateChanged
        )
        self.connect(
            self.detector_distance,
            "positionChanged",
            self.dtoxPositionChanged
        )
        self.connect(HWR.beamline.energy, "valueChanged", self.energyChanged)

    def isReady(self):
        if self.valid:
            try:
                return self.detector_distance.isReady()
            except BaseException:
                return False
        return False

    def get_beam_centre(self, dist=None):
        if dist is None:
            dist = self.detector_distance.getPosition()
        ax = float(HWR.beamline.detector["beam"].getProperty("ax"))
        bx = float(HWR.beamline.detector["beam"].getProperty("bx"))
        ay = float(HWR.beamline.detector["beam"].getProperty("ay"))
        by = float(HWR.beamline.detector["beam"].getProperty("by"))

        return float(dist * ax + bx), float(dist * ay + by)

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius = min(
            self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y
        )

    def getWavelength(self):
        try:
            return HWR.beamline.energy.get_current_wavelength()
        except BaseException:
            current_en = HWR.beamline.energy.getPosition()
            if current_en:
                return 12.3984 / current_en
            return None

    def energyChanged(self, egy):
        return self.recalculateResolution()

    def res2dist(self, res=None):
        current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        ax = float(HWR.beamline.detector["beam"].getProperty("ax"))
        bx = float(HWR.beamline.detector["beam"].getProperty("bx"))
        ay = float(HWR.beamline.detector["beam"].getProperty("ay"))
        by = float(HWR.beamline.detector["beam"].getProperty("by"))

        try:
            ttheta = 2 * math.asin(current_wavelength / (2 * res))

            dist_1 = bx / (math.tan(ttheta) - ax)
            dist_2 = by / (math.tan(ttheta) - ay)
            dist_3 = (self.det_width - bx) / (math.tan(ttheta) + ax)
            dist_4 = (self.det_height - by) / (math.tan(ttheta) + ay)

            return min(dist_1, dist_2, dist_3, dist_4)
        except BaseException:
            return None

    def _calc_res(self, radius, dist):
        current_wavelength = self.getWavelength()

        try:
            ttheta = math.atan(radius / dist)

            if ttheta != 0:
                return current_wavelength / (2 * math.sin(ttheta / 2))
            else:
                return None
        except Exception:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def dist2res(self, dist=None):
        if dist is None:
            dist = self.detector_distance.getPosition()

        return self._calc_res(self.det_radius, dist)

    def recalculateResolution(self):
        dtox_pos = self.detector_distance.getPosition()
        self.update_beam_centre(dtox_pos)
        new_res = self.dist2res(dtox_pos)
        if new_res is None:
            return
        self.update_resolution(new_res)

    def getPosition(self):
        if self.currentResolution is None:
            self.recalculateResolution()
        return self.currentResolution

    def get_value_at_corner(self):
        dtox_pos = self.detector_distance.getPosition()
        beam_x, beam_y = self.get_beam_centre(dtox_pos)

        distance_at_corners = [
            math.sqrt(beam_x ** 2 + beam_y ** 2),
            math.sqrt((self.det_width - beam_x) ** 2 + beam_y ** 2),
            math.sqrt((beam_x ** 2 + (self.det_height - beam_y) ** 2)),
            math.sqrt((self.det_width - beam_x) ** 2 + (self.det_height - beam_y) ** 2),
        ]
        return self._calc_res(max(distance_at_corners), dtox_pos)

    def update_resolution(self, res):
        self.currentResolution = res
        self.emit("positionChanged", (res,))
        self.emit("valueChanged", (res,))

    def getState(self):
        return self.detector_distance.getState()

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.dtoxStateChanged(self.detector_distance.getState())

    def dtoxStateChanged(self, state):
        self.emit("stateChanged", (state,))
        if state == self.detector_distance.READY:
            self.recalculateResolution()

    def dtoxPositionChanged(self, pos):
        self.update_beam_centre(pos)
        self.update_resolution(self.dist2res(pos))

    def getLimits(self):
        low, high = self.detector_distance.getLimits()

        return (self.dist2res(low), self.dist2res(high))

    def move(self, pos, wait=False):
        logging.getLogger().info(
            "move Resolution to %s (%f mm)", pos, self.res2dist(pos)
        )

        if wait:
           self.detector_distance.syncMove(self.res2dist(pos))
        else:
            self.detector_distance.move(self.res2dist(pos))

    def motorIsMoving(self):
        return self.detector_distance.motorIsMoving()

    def stop(self):
        try:
           self.detector_distance.stop()
        except BaseException:
            pass

import logging
import math
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.HardwareObjects.Resolution import Resolution


class ResolutionMockup(Resolution):
    def _init(self):
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        return BaseHardwareObjects.Equipment._init(self)

    def init(self):
        super(ResolutionMockup, self).init()
        self._nominal_value = 3
        self.detmState = None
        self.state = self.STATES.READY
        self.connect(
            HWR.beamline.detector.distance, "valueChanged", self.dtoxPositionChanged
        )

        # # Default value detector radius - corresponds to Eiger 16M:
        # self.det_radius = 155.625
        # detector = HWR.beamline.detector
        # if detector is not None:
        #     # Calculate detector radius
        #     px = float(detector.getProperty("px", default_value=0))
        #     py = float(detector.getProperty("py", default_value=0))
        #     width = float(detector.getProperty("width", default_value=0))
        #     height = float(detector.getProperty("height", default_value=0))
        #     det_radius = 0.5 * min(px * width, py * height)
        #     if det_radius > 0:
        #         self.det_radius = det_radius

        HWR.beamline.detector.distance.set_value(self.res2dist())

    def beam_centre_updated(self, beam_pos_dict):
        pass

    def dtoxPositionChanged(self, pos):
        self.update_value(self.dist2res(pos))

    def wavelengthChanged(self, pos=None):
        self.recalculateResolution()

    def energyChanged(self, energy):
        self.wavelengthChanged(12.3984 / energy)

    # def res2dist(self, res=None):
    #     if res is None:
    #         res = self._nominal_value
    #     try:
    #         ttheta = 2 * math.asin(HWR.beamline.energy.get_wavelength() / (2 * res))
    #         return self.det_radius / math.tan(ttheta)
    #
    #     except BaseException:
    #         return None
    #
    # def dist2res(self, dist=None):
    #     if dist is None:
    #         logging.getLogger("HWR").error(
    #             "Refusing to calculate resolution from distance 'None'"
    #         )
    #         return
    #     try:
    #         ttheta = math.atan(self.det_radius / dist)
    #         if ttheta != 0:
    #             return HWR.beamline.energy.get_wavelength() / (2 * math.sin(ttheta / 2))
    #     except BaseException:
    #         logging.getLogger().exception("error while calculating resolution")
    #         return None

    # def recalculateResolution(self):
    #     self._nominal_value = self.dist2res(
    #         HWR.beamline.detector.distance.get_value()
    #     )

    # def equipmentReady(self):
    #     self.emit("deviceReady")
    #
    # def equipmentNotReady(self):
    #     self.emit("deviceNotReady")

    def get_value(self):
        if self._nominal_value is None:
            self.recalculateResolution()
        return self._nominal_value

    def get_state(self):
        return self.state

    def connectNotify(self, signal):
        pass

    def detmStateChanged(self, state):
        pass

    def detmPositionChanged(self, pos):
        pass

    def get_limits(self):
        return (0, 20)

    def set_position(self, pos, wait=True):
        HWR.beamline.detector.distance.set_value(self.res2dist(pos), wait=wait)

    # move = set_position
    #
    # def motorIsMoving(self):
    #     return (
    #         HWR.beamline.detector.distance.motorIsMoving() or HWR.beamline.energy.moving
    #     )

    def abort(self):
        HWR.beamline.detector.distance.abort()

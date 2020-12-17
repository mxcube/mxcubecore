import logging
from mx3core.hardware_objects import Resolution
import math

from mx3core import HardwareRepository as HWR


class BIOMAXResolution(Resolution.Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.Resolution.__init__(self, *args, **kwargs)

    def init(self):

        detector = HWR.beamline.detector

        if detector:
            try:
                self.det_width = detector.get_x_pixels_in_detector()
                self.det_height = detector.get_y_pixels_in_detector()
            except Exception:
                self.det_width = 4150
                self.det_height = 4371

            else:
                self.valid = False
                logging.getLogger().exception("Cannot get detector size")

        self.connect(detector.distance, "stateChanged", self.dtoxStateChanged)
        self.connect(detector.distance, "valueChanged", self.dtoxPositionChanged)
        self.connect(HWR.beamline.energy, "valueChanged", self.energyChanged)
        self.connect(detector, "roiChanged", self.det_roi_changed)

    def res2dist(self, res=None):
        current_wavelength = HWR.beamline.energy.get_wavelength()

        if res is None:
            res = self._nominal_value

        try:
            ttheta = 2 * math.asin(current_wavelength / (2 * res))
            return HWR.beamline.detector.get_radius() / math.tan(ttheta)
        except Exception as ex:
            print(ex)
            return None

    def dist2res(self, dist=None):
        detector_HO = HWR.beamline.detector
        if dist is None:
            dist = detector_HO.distance.get_value()

        return "%.3f" % self._calc_res(detector_HO.get_radius, dist)

    def det_roi_changed(self):
        self.det_width = HWR.beamline.detector.get_x_pixels_in_detector()
        self.det_height = HWR.beamline.detector.get_y_pixels_in_detector()
        self.recalculateResolution()

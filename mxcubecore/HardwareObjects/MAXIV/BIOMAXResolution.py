import logging
from HardwareRepository.HardwareObjects import Resolution
import math

from HardwareRepository import HardwareRepository as HWR


class BIOMAXResolution(Resolution.Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.Resolution.__init__(self, *args, **kwargs)

    def init(self):
        self.currentResolution = None

        detector = HWR.beamline.detector

        if detector:
            try:
                self.det_width = detector.get_x_pixels_in_detector()
                self.det_height = detector.get_y_pixels_in_detector()
            except BaseException:
                self.det_width = 4150
                self.det_height = 4371

            else:
                self.valid = False
                logging.getLogger().exception("Cannot get detector size")

        self.update_beam_centre(detector.distance.get_value())
        self.connect(detector.distance, "stateChanged", self.dtoxStateChanged)
        self.connect(detector.distance, "valueChanged", self.dtoxPositionChanged)
        self.connect(HWR.beamline.energy, "valueChanged", self.energyChanged)
        self.connect(detector, "roiChanged", self.det_roi_changed)

    def res2dist(self, res=None):
        current_wavelength = HWR.beamline.energy.get_wavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2 * math.asin(current_wavelength / (2 * res))
            return self.det_radius / math.tan(ttheta)
        except Exception as ex:
            print(ex)
            return None

    def dist2res(self, dist=None):
        if dist is None:
            dist = HWR.beamline.detector.distance.get_value()

        return "%.3f" % self._calc_res(self.det_radius, dist)

    def det_roi_changed(self):
        self.det_width = HWR.beamline.detector.get_x_pixels_in_detector()
        self.det_height = HWR.beamline.detector.get_y_pixels_in_detector()
        self.update_beam_centre(HWR.beamline.detector.distance.get_value())
        self.recalculateResolution()

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius = (
            min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)
            * 0.075
        )

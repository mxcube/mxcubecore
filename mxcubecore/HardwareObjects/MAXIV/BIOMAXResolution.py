import logging
from HardwareRepository.HardwareObjects import Resolution
import math

from HardwareRepository import HardwareRepository
beamline_object = HardwareRepository.get_beamline()

class BIOMAXResolution(Resolution.Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.Resolution.__init__(self, *args, **kwargs)

    def init(self):
        self.currentResolution = None

        detector = beamline_object.detector

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

        self.update_beam_centre(detector.detector_distance.getPosition())
        self.connect(detector.detector_distance, "stateChanged", self.dtoxStateChanged)
        self.connect(detector.detector_distance, "positionChanged", self.dtoxPositionChanged)
        self.connect(beamline_object.energy, "valueChanged", self.energyChanged)
        self.connect(detector, "roiChanged", self.det_roi_changed)

    def res2dist(self, res=None):
        current_wavelength = self.getWavelength()

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
            dist = beamline_object.detector.detector_distance.getPosition()

        return "%.3f" % self._calc_res(self.det_radius, dist)

    def det_roi_changed(self):
        self.det_width = beamline_object.detector.get_x_pixels_in_detector()
        self.det_height = beamline_object.detector.get_y_pixels_in_detector()
        self.update_beam_centre(beamline_object.detector.detector_distance.getPosition())
        self.recalculateResolution()

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius = (
            min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)
            * 0.075
        )

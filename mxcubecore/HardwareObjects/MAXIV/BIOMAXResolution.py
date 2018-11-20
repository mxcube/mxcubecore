import logging
from HardwareRepository import HardwareRepository
import Resolution
import math


class BIOMAXResolution(Resolution.Resolution):
    def __init__(self, *args, **kwargs):
        Resolution.Resolution.__init__(self, *args, **kwargs)

    def init(self):
        self.currentResolution = None
        self.energy = None

        self.dtox = self.getObjectByRole("dtox")
        self.energy = self.getObjectByRole("energy")
        self.detector = self.getObjectByRole("detector")

        if self.detector:
            try:
                self.det_width = self.detector.get_x_pixels_in_detector()
                self.det_height = self.detector.get_y_pixels_in_detector()
            except BaseException:
                self.det_width = 4150
                self.det_height = 4371

            else:
                self.valid = False
                logging.getLogger().exception("Cannot get detector size")

        self.update_beam_centre(self.dtox.getPosition())
        self.connect(self.dtox, "stateChanged", self.dtoxStateChanged)
        self.connect(self.dtox, "positionChanged", self.dtoxPositionChanged)
        self.connect(self.energy, "valueChanged", self.energyChanged)
        self.connect(self.detector, "roiChanged", self.det_roi_changed)

    def res2dist(self, res=None):
        current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2 * math.asin(current_wavelength / (2 * res))
            return self.det_radius / math.tan(ttheta)
        except Exception as ex:
            print ex
            return None

    def dist2res(self, dist=None):
        if dist is None:
            dist = self.dtox.getPosition()

        return "%.3f" % self._calc_res(self.det_radius, dist)

    def det_roi_changed(self):
        self.det_width = self.detector.get_x_pixels_in_detector()
        self.det_height = self.detector.get_y_pixels_in_detector()
        self.update_beam_centre(self.dtox.getPosition())
        self.recalculateResolution()

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius = (
            min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)
            * 0.075
        )

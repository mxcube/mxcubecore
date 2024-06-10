import logging
from mxcubecore.HardwareObjects import Resolution
from mxcubecore.HardwareObjects.abstract.AbstractResolution import AbstractResolution

import math
from scipy.constants import kilo, h, c, eV, angstrom


class BIOMAXResolution(AbstractResolution):
    def __init__(self, *args, **kwargs):
        AbstractResolution.__init__(self, *args, **kwargs)

    def init(self):
        self.energy = None

        self.dtox = self.get_object_by_role("dtox")
        self.energy = self.get_object_by_role("energy")
        self.detector = self.get_object_by_role("detector")

        if self.detector:
            try:
                self.det_width = self.detector.get_x_pixels_in_detector()
                self.det_height = self.detector.get_y_pixels_in_detector()
            except:
                self.det_width = 4150
                self.det_height = 4371

        else:
            self.valid = False
            logging.getLogger().exception("Cannot get detector size")

        self.update_beam_centre(self.dtox.get_value())
        self.connect(self.dtox, "stateChanged", self.dtox_state_changed)
        self.connect(self.dtox, "valueChanged", self.dtox_position_changed)
        self.connect(self.detector, "roiChanged", self.det_roi_changed)

        super().init()

    def dtox_state_changed(self, state=None):
        self.update_detector_state()

    def update_detector_state(self, state=None):
        self.emit("stateChanged", state)

    def dtox_position_changed(self, state=None):
        self.update_detector_position()

    def update_detector_position(self, state=None):
        self.emit("valueChanged", state)

    def det_roi_changed(self):
        self.det_width = self.detector.get_x_pixels_in_detector()
        self.det_height = self.detector.get_y_pixels_in_detector()
        self.update_beam_centre(self.dtox.get_value())
        self.recalculate_resolution()

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius = (
            min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)
            * 0.075
        )

    def get_beam_centre(self, dtox=None):
        if dtox is None:
            dtox = self.dtox.get_value()
        ax = float(self.detector["beam"].get_property("ax"))
        bx = float(self.detector["beam"].get_property("bx"))
        ay = float(self.detector["beam"].get_property("ay"))
        by = float(self.detector["beam"].get_property("by"))

        return float(dtox) * ax + bx, float(dtox) * ay + by

    def recalculate_resolution(self):
        self.current_resolution = self.dist2res(self.dtox.get_value())
        if self.current_resolution is None:
            return
        self.update_resolution(self.current_resolution)

    def dist2res(self, dist=None):
        if dist is None:
            dist = self.dtox.get_value()

        return round(self._calc_res(self.det_radius, dist), 3)

    def get_value(self):
        return self.dist2res(self.dtox.get_value())

    def get_limits(self):
        """Return resolution low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        _low, _high = self.dtox.get_limits()

        return (
            self.dist2res(_low),
            self.dist2res(_high),
        )

    def _set_value(self, value):
        """Move resolution to value.
        Args:
            value (float): target value [Å]
        """
        distance = self.res2dist(value)
        msg = "Move resolution to {} ({} mm)".format(value, distance)
        logging.getLogger().info(msg)
        self.dtox.set_value(float(distance))

    def _calc_res(self, radius, dist):
        current_wavelength = self.get_wavelength()

        try:
            ttheta = math.atan(radius / dist)

            if ttheta != 0:
                return current_wavelength / (2 * math.sin(ttheta / 2))
            else:
                return None
        except Exception:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def get_wavelength(self):
        return self.get_wavelegth_from_energy(self.energy.get_current_energy())

    def get_wavelegth_from_energy(self, energy):
        return (h * c) / (eV * angstrom * kilo) / energy

    def update_resolution(self, res):
        self.current_resolution = res
        self.emit("valueChanged", (res,))

    def res2dist(self, res=None):
        current_wavelength = self.get_wavelength()

        if res is None:
            res = self.current_resolution

        try:
            ttheta = 2 * math.asin(current_wavelength / (2 * res))
            return self.det_radius / math.tan(ttheta)
        except Exception as ex:
            print(ex)
            return None

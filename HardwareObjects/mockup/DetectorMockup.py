from HardwareRepository.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)


class DetectorMockup(AbstractDetector):
    """
    Descript. : Detector class. Contains all information about detector
                the states are 'OK', and 'BAD'
                the status is busy, exposing, ready, etc.
                the physical property is RH for pilatus, P for rayonix
    """

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractDetector.__init__(self, name)

    def init(self):
        """
        Descript. :
        """
        AbstractDetector.init(self)

        self._temperature = 25
        self._humidity = 60
        self.actual_frame_rate = 50
        self._roi_modes_list = ("0", "C2", "C16")
        self._roi_mode = 0
        self._exposure_time_limits = [0.04, 60000]
        self.status = "ready"

    def set_roi_mode(self, roi_mode):
        self._roi_mode = roi_mode
        self.emit("detectorRoiModeChanged", (self._roi_mode,))

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        """Get approx detector centre """
        xval, yval = super(DetectorMockup, self).get_beam_position(
            distance=distance, wavelength=wavelength
        )
        if None in (xval, yval):
            # default to Pilatus values
            xval = self.getProperty("width", 2463) / 2.0 + 0.4
            yval = self.getProperty("height", 2527) / 2.0 + 0.4
        return xval, yval

    def re_emit_values(self):
        self.emit("detectorModeChanged", (self._roi_mode,))
        self.emit("temperatureChanged", (self._temperature, True))
        self.emit("humidityChanged", (self._humidity, True))
        self.emit("expTimeLimitsChanged", (self._exposure_time_limits,))
        self.emit("frameRateChanged", self.actual_frame_rate)
        self.emit("statusChanged", (self.status, "Ready"))

    def prepare_acquisition(self, *args, **kwargs):
        """
        Prepares detector for acquisition
        """
        return

    def start_acquisition(self):
        """
        Starts acquisition
        """
        return

    def stop_acquisition(self):
        """
        Stops acquisition
        """
        return

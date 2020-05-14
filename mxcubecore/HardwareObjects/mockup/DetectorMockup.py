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
        self._actual_frame_rate = 50
        self._roi_modes_list = ("0", "C2", "C16")
        self._roi_mode = 0
        self._exposure_time_limits = [0.04, 60000]
        self.update_state(self.STATES.READY)

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


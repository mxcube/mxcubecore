from mxcubecore.HardwareObjects.abstract.AbstractDetector import (
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
        self._roi_modes_list = eval(
            self.get_property("roi_mode_list", '["0", "C2", "C16"]')
        )
        self._roi_mode = 0
        self._exposure_time_limits = eval(
            self.get_property("exposure_time_limits", "[0.04, 60000]")
        )
        self.update_state(self.STATES.READY)
        self.distance_motor_hwobj = self.get_object_by_role("detector_distance")

        """Get approx detector centre (default to Pilatus values)"""
        xval = self.get_property('width', 2463)/2. + 0.4
        yval = self.get_property('height', 2527)/2. + 0.4
        self._beam_centre = (xval, yval)

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        return  self._beam_centre

    def _set_beam_centre(self, beam_centre):
        # Needed for GPhL collection emulation
        self._beam_centre = beam_centre

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

    def restart(self) -> None:
        pass
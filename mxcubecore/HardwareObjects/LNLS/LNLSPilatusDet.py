import time
import logging

from HardwareRepository.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
import epics


class LNLSPilatusDet(AbstractDetector):

    DET_THRESHOLD = 'det_threshols_energy'
    #DET_STATUS = 'det_status_message'

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

        # self.distance = 500
        self._temperature = 25
        self._humidity = 60
        self.actual_frame_rate = 50
        self._roi_modes_list = ("0", "C2", "C16")
        self._roi_mode = 0
        self._exposure_time_limits = [0.04, 60000]
        self.status = "ready"
        self.pv_status = epics.PV(self.getProperty("channel_status"))
        self.threshold = -1  # Starts with invalid value. To be set.

        self._distance_motor_hwobj = self.getObjectByRole("detector_distance")
        self.threshold = self.get_threshold_energy()

    def set_roi_mode(self, roi_mode):
        self._roi_mode = roi_mode
        self.emit("detectorModeChanged", (self._roi_mode,))

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_position(self, distance=None):
        """Get approx detector centre """
        xval, yval = super(LNLSPilatusDet, self).get_beam_position(distance=distance)
        if None in (xval, yval):
            # default to Pilatus values
            xval = self.getProperty("width", 2463) / 2.0 + 0.4
            yval = self.getProperty("height", 2527) / 2.0 + 0.4
        return xval, yval

    def update_values(self):
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

    def last_image_saved(self):
        """
        Returns:
            str: path to last image
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

    def get_threshold_energy(self):
        """
        Returns:
            float: threshold energy
        """
        value = float(self.get_channel_value(self.DET_THRESHOLD))
        return value

    def set_threshold_energy(self, energy):
        """
        Set threshold energy and returns whether it was successful or not.
        """
        target_threshold = energy / 2
        if self.threshold == target_threshold:
            return True

        logging.getLogger("HWR").info(
            "Setting Pilatus threshold..."
        )
        self.set_channel_value(self.DET_THRESHOLD, target_threshold)

        # wait for threshold setting to be done
        time.sleep(2)
        # Using epics because we need 'as_string' option
        status = self.pv_status.get(as_string=True)
        logging.getLogger("HWR").info('Pilatus status: %s' % status)

        while status == "Setting threshold":
            logging.getLogger("HWR").info(
                'Pilatus status: %s (this may take a minute)...' % status
            )
            time.sleep(3)
            status = self.pv_status.get(as_string=True)

        current_threshold = self.get_threshold_energy()
        logging.getLogger("HWR").info(
            'Pilatus: current threshold is %s (target is %s)' %
            (current_threshold, target_threshold)
        )
        if (status == "Camserver returned OK"
        and current_threshold == target_threshold):
            logging.getLogger("HWR").info('Pilatus status: %s' % status)
            logging.getLogger("HWR").info(
                "Pilatus threshold successfully set."
            )
            return True

        logging.getLogger("HWR").error('Pilatus status: %s' % status)
        logging.getLogger("HWR").error(
            "Error while setting Pilatus threshold. Please, check the detector."
        )
        return False

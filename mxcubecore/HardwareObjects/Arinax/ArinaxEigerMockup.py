"""
Derived from BIOMAXEigerMockup
"""

import gevent
import time
import copy
import logging

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.TaskUtils import task, cleanup, error_cleanup
# from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.HardwareObjects.abstract.AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject

class ArinaxEigerMockup(AbstractDetector, HardwareObject):
    """
    Description: Eiger hwobj based on tango
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        AbstractDetector.__init__(self, name)
        HardwareObject.__init__(self, name)

        self.device = None
        self.file_suffix = None
        self.default_exposure_time = 0.1
        self.default_compression = "bslz4"
        self.buffer_limit = None
        self.dcu = None
        self.config_state = None
        self.initialized = False
        self.status_chan = None
        self.roi_mode = "dsiabled"
        self.photon_energy = 12
        self.energy_threshold = 6000
        self.distance_motor_hwobj = None
        # defaults
        self.energy_change_threshold_default = 20

    def init(self):

        AbstractDetector.init(self)
        HardwareObject.init(self)

        self.distance_motor_hwobj = self.getObjectByRole("distance_motor")

        self.file_suffix = self.getProperty("file_suffix")
        self.default_exposure_time = self.getProperty("default_exposure_time")
        self.default_compression = self.getProperty("default_compression")
        self.buffer_limit = self.getProperty("buffer_limit")
        self.dcu = self.getProperty("dcu")

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        self.col_config = {
            "omega_start": 0,
            "omega_increment": 0.1,
            "beam_center_x": 2000,  # length not pixel
            "beam_center_y": 2000,
            "detector_distance": 0.15,
            "count_time": 0.1,
            "nimages": 100,
            "ntrigger": 1,
            "nimages_per_file": {"value": 1, "api_name": "filewriter"},
            "roi_mode": "disabled",
            "name_pattern": {"value": "test", "api_name": "filewriter"},
            "photon_energy": 12000,
            "trigger_mode": "exts",
        }

        # we need to call the init device before accessing the channels here
        #   otherwise the initialization is triggered by the HardwareRepository Poller
        #   that is delayed after the application starts

        try:
            self.energy_change_threshold = float(
                self.getProperty("min_trigger_energy_change")
            )
        except Exception:
            self.energy_change_threshold = self.energy_change_threshold_default

        self.update_state(self.STATES.READY)

    def get_state(self):
        """Get the motor state.
        Returns:
            (enum HardwareObjectState): Motor state.
        """
        return self.distance_motor_hwobj.get_state()

    def get_deadtime(self):
        return 0.01

    def get_distance(self):
        """
        Descript. :
        """
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getPosition()
        else:
            return self.default_distance

    def get_limits(self):
        """
        Descript. :
        """
        return 50, 500
        # TODO Implement limits in Motor HardwareObject

    def get_readout_time(self):
        return 0.000004

    def get_acquisition_time(self):
        return 2

    def get_roi_mode(self):
        return self.roi_mode

    def set_roi_mode(self, value):
        self.roi_mode = value

    def get_pixel_size_x(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """
        x_pixel_size = 0.000075
        return x_pixel_size * 1000

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along y-axis respectively
        unit, mm
        """
        y_pixel_size = 0.000075
        return y_pixel_size * 1000

    def get_x_pixels_in_detector(self):
        """
        number of pixels along x-axis
        numbers vary depending on the RoiMode
        """
        return 4150

    def get_y_pixels_in_detector(self):
        """
        number of pixels along y-axis,
        numbers vary depending on the RoiMode
        """
        return 4371

    def get_minimum_exposure_time(self):
        return 0.01

    def get_sensor_thickness(self):
        return 0.45

    def has_shutterless(self):
        return True

    #  GET INFORMATION END

    #  SET VALUES
    def set_photon_energy(self, energy):
        """
        set photon_energy
        Note, the readout_time will be changed
        engery, in eV
        """
        self.photon_energy = energy
        return True

    def set_energy_threshold(self, threshold):
        """
        set energy_threshold
        Note, the readout_time will be changed
        By deafult, the value is 50% of the photon_energy and will be
        updated upon setting PhotonEnergy. If other values are needed,
        this should be set after changing PhotonEnergy.
        Eengery, in eV
        """
        self.energy_threshold = threshold

    #  SET VALUES END

    def wait_config_done(self):
        # TODO Method for managing the waiting for detector ready
        pass

    def clear(self):
        pass

    def wait_idle(self):
        pass

    def get_file_list(self):
        return None

    def prepare_acquisition(self, config):
        """
        config is a dictionary
        OmegaStart,OmegaIncrement,
        BeamCenterX
        BeamCenterY
        OmegaStart
        OmegaIncrement
        start, osc_range, exptime, ntrigger, number_of_images, images_per_file, compression,ROI,wavelength):
        """

        logging.getLogger("user_level_log").info("Preparing acquisition")

    @task
    def start_acquisition(self):
        """
        Before starting the acquisition a prepare_acquisition should be issued
        After prepare_acquisition the detector should be in "idle" state

        Otherwise you will have to send a "disarm" command by hand to be able to
        start an acquisition
        """

        logging.getLogger("user_level_log").info("Detector armed")

        return self.arm()

    def stop_acquisition(self):
        """
        when use external trigger, Disarm is required, otherwise the last h5 will
        not be released and not available in WebDAV.
        """

        try:
            self.cancel()  # this is needed as disarm in tango device server does not seem to work
            # as expected. the disarm command in the simpleinterface is always working
            # when called from Tango it does not. Once bug is solved in tango server, the
            # call to "cancel()" is not necessary here
            self.disarm()
        except Exception:
            pass

    def cancel_acquisition(self):
        """Cancel acquisition"""
        try:
            self.cancel()
        except Exception:
            pass

        time.sleep(1)
        self.disarm()

    def arm(self):
        return

    def trigger(self):
        return

    def disarm(self):
        return

    def cancel(self):
        return

    def abort(self):
        return

    def set_collection_uuid(self, col_uuid):
        # TODO
        pass

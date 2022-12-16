"""

  File:  BIOMAXEigerMockup.py

  Description:  This module implements the hardware object for the Eiger detector
     based on a Tango device server


Detector Status:
-----------------

hardware status:
   ready:   ready for trigger (this is the state after an "Arm" command)
   idle:    ready for config (this should be the state after a "Disarm" command)

hardware object status:

   configuring:  a configuration task is ongoing


"""

import gevent
import time
import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.TaskUtils import task, cleanup, error_cleanup
from mxcubecore.BaseHardwareObjects import Equipment


class BIOMAXEigerMockup(Equipment):
    """
    Description: Eiger hwobj based on tango
    """

    def __init__(self, *args):
        """
        Descrip. :
        """
        Equipment.__init__(self, *args)

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
        self.photon_energy = 12000
        self.energy_threshold = 6000

        # defaults
        self.energy_change_threshold_default = 20

    def init(self):

        tango_device = self.get_property("detector_device")
        filewriter_device = self.get_property("filewriter_device")

        self.file_suffix = self.get_property("file_suffix")
        self.default_exposure_time = self.get_property("default_exposure_time")
        self.default_compression = self.get_property("default_compression")
        self.buffer_limit = self.get_property("buffer_limit")
        self.dcu = self.get_property("dcu")

        # config needed to be set up for data collection
        # if values are None, use the one from the system
        self.col_config = {
            "OmegaStart": 0,
            "OmegaIncrement": 0.1,
            "BeamCenterX": 2000,  # length not pixel
            "BeamCenterY": 2000,
            "DetectorDistance": 0.15,
            "CountTime": 0.1,
            "NbImages": 100,
            "NbTriggers": 1,
            "ImagesPerFile": 100,
            "RoiMode": "disabled",
            "FilenamePattern": "test",
            "PhotonEnergy": 12000,
            "TriggerMode": "exts",
        }

        # we need to call the init device before accessing the channels here
        #   otherwise the initialization is triggered by the HardwareRepository Poller
        #   that is delayed after the application starts

        try:
            self.energy_change_threshold = float(
                self.get_property("min_trigger_energy_change")
            )
        except Exception:
            self.energy_change_threshold = self.energy_change_threshold_default

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

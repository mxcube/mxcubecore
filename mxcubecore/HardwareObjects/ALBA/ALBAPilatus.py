#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import logging
import time

from mxcubecore.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
from mxcubecore.BaseHardwareObjects import HardwareObject

from PyTango.gevent import DeviceProxy

__author__ = "Vicente Rey"
__credits__ = ["ALBA"]
__version__ = "2.3."
__category__ = "General"


class ALBAPilatus(AbstractDetector, HardwareObject):
    """Detector class. Contains all information about detector
       - states are 'OK', and 'BAD'
       - status is busy, exposing, ready, etc.
       - physical property is RH for pilatus, P for rayonix
    """

    def __init__(self, name):
        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)

        self.distance_motor_hwobj = None
        self.default_distance = None
        self.default_distance_limits = None

        self.default_latency_time = 0.003

        self.exp_time_limits = None

        self.headers = {}

    def init(self):
        self.distance_motor_hwobj = self.get_object_by_role("distance_motor")
        self.devname = self.get_property("tangoname")

        try:
            self.latency_time = float(self.get_property("latency_time"))
        except Exception:
            self.latency_time = None

        if self.latency_time is None:
            logging.getLogger("HWR").debug(
                "Cannot obtain latency time from Pilatus XML. Using %s"
                % self.default_latency_time
            )
            self.latency_time = self.default_latency_time

        self.devspecific = self.get_property("device_specific")

        exp_time_limits = self.get_property("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))

        self.device = DeviceProxy(self.devname)
        self.device_specific = DeviceProxy(self.devspecific)
        self.device.set_timeout_millis(30000)

        self.beamx_chan = self.get_channel_object("beamx")
        self.beamy_chan = self.get_channel_object("beamy")

    def start_acquisition(self):
        self.device.startAcq()

    def stop_acquisition(self):
        self.device.abortAcq()

    def wait_move_distance_done(self):
        self.distance_motor_hwobj.wait_end_of_move()

    def get_threshold(self):
        return self.device_specific.threshold

    def get_threshold_gain(self):
        return self.device_specific.threshold_gain

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        """Returns beam center coordinates"""

        # NBNB TODO check if pixels or mm, and adjust code
        # Should be pixels
        beam_x = 0
        beam_y = 0
        try:
            beam_x = self.beamx_chan.get_value()
            beam_y = self.beamy_chan.get_value()
        except Exception:
            pass
        return beam_x, beam_y

    def get_manufacturer(self):
        return self.get_property("manufacturer")
        return "Dectris"

    def get_model(self):
        return self.get_property("model")

    def get_detector_type(self):
        return self.get_property("type")

    def get_default_exposure_time(self):
        return self.get_property("default_exposure_time")

    def get_minimum_exposure_time(self):
        return self.get_property("minimum_exposure_time")

    def get_exposure_time_limits(self):
        """Returns exposure time limits as list with two floats"""
        return self.exp_time_limits

    def get_file_suffix(self):
        return self.get_property("file_suffix")

    def get_pixel_size(self):
        return self.get_property("px"), self.get_property("py")

    # methods for data collection
    def set_energy_threshold(self):
        eugap_ch = self.get_channel_object("eugap")

        try:
            currentenergy = eugap_ch.get_value()
        except Exception:
            currentenergy = 12.6

        det_energy = self.get_threshold()

        # threshold = det_energy  / 2.
        # limitenergy = threshold / 0.8

        if round(currentenergy, 6) < 7.538:
            currentenergy = 7.538

        kev_diff = abs(det_energy - currentenergy)

        if kev_diff > 1.2:
            logging.getLogger("HWR").debug(
                "programming energy_threshold on pilatus to: %s" % currentenergy
            )
            # if self.wait_standby():
            # self.device_specific.energy_threshold = currentenergy

    def get_latency_time(self):
        return self.latency_time

    def wait_standby(self, timeout=300):
        t0 = time.time()
        while self.device_specific.cam_state == "STANDBY":
            if time.time() - t0 > timeout:
                print("timeout waiting for Pilatus to be on STANDBY")
                return False
            time.sleep(0.1)
        return True

    def prepare_acquisition(self, dcpars):

        self.set_energy_threshold()
        # self.wait_standby()

        osc_seq = dcpars["oscillation_sequence"][0]
        file_pars = dcpars["fileinfo"]

        basedir = file_pars["directory"]
        prefix = "%s_%s_" % (file_pars["prefix"], file_pars["run_number"])

        first_img_no = osc_seq["start_image_number"]
        nb_frames = osc_seq["number_of_images"]
        exp_time = osc_seq["exposure_time"]

        fileformat = "CBF"
        trig_mode = "EXTERNAL_TRIGGER"
        # latency_time = 0.003

        logging.getLogger("HWR").debug(
            " Preparing detector (dev=%s) for data collection" % self.devname
        )

        logging.getLogger("HWR").debug("    /saving directory: %s" % basedir)
        logging.getLogger("HWR").debug("    /prefix          : %s" % prefix)
        logging.getLogger("HWR").debug("    /saving_format   : %s" % fileformat)
        logging.getLogger("HWR").debug("    /trigger_mode    : %s" % trig_mode)
        logging.getLogger("HWR").debug("    /acq_nb_frames   : %s" % nb_frames)
        logging.getLogger("HWR").debug(
            "    /acq_expo_time   : %s" % str(exp_time - self.latency_time)
        )
        logging.getLogger("HWR").debug("    /latency_time    : %s" % self.latency_time)

        self.device.write_attribute("saving_mode", "AUTO_FRAME")
        self.device.write_attribute("saving_directory", basedir)
        self.device.write_attribute("saving_prefix", prefix)
        self.device.write_attribute("saving_format", fileformat)

        # set ROI and header in limaserver
        #  TODO

        TrigList = [
            "INTERNAL_TRIGGER",
            "EXTERNAL_TRIGGER",
            "EXTERNAL_TRIGGER_MULTI",
            "EXTERNAL_GATE",
            "EXTERNAL_START_STOP",
        ]

        self.device.write_attribute("acq_trigger_mode", trig_mode)
        self.device.write_attribute("acq_expo_time", exp_time - self.latency_time)
        self.device.write_attribute("latency_time", self.latency_time)

        return True

    def prepare_collection(self, nb_frames, first_img_no):
        logging.getLogger("HWR").debug(
            "ALBAPilatus. preparing collection. nb_images: %s, first_no: %s"
            % (nb_frames, first_img_no)
        )
        self.device.write_attribute("acq_nb_frames", nb_frames)
        self.device.write_attribute("saving_next_number", first_img_no)
        self.device.prepareAcq()
        return True

    def start_collection(self):
        self.start_acquisition()

    def stop_collection(self):
        self.stop_acquisition()

    def set_image_headers(self, image_headers, angle_info):

        nb_images = image_headers["nb_images"]
        angle_inc = image_headers["Angle_increment"]
        start_angle = image_headers["Start_angle"]

        startangles_list = list()
        ang_start, ang_inc, spacing = angle_info
        for i in range(nb_images):
            startangles_list.append("%0.4f deg." % (ang_start + spacing * i))

        headers = list()
        for i, sa in enumerate(startangles_list):
            header = (
                "_array_data.header_convention PILATUS_1.2\n"
                "# Detector: PILATUS 6M, S/N 60-0108, Alba\n"
                "# %s\n"
                "# Pixel_size 172e-6 m x 172e-6 m\n"
                "# Silicon sensor, thickness 0.000320 m\n"
                % time.strftime("%Y/%b/%d %T")
            )

            # Acquisition values (headers dictionary) but overwrites start angle
            image_headers["Start_angle"] = sa
            for key, value in image_headers.items():
                if key == "nb_images":
                    continue
                header += "# %s %s\n" % (key, value)
            headers.append("%d : array_data/header_contents|%s;" % (i, header))

        self.device.write_attribute("saving_header_delimiter", ["|", ";", ":"])
        self.device.resetCommonHeader()
        self.device.resetFrameHeaders()
        self.device.setImageHeader(headers)


def test_hwo(hwo):
    print("Detector Distance is: ", hwo.distance.get_value())
    print("   Beam X: %s / Beam Y: %s" % hwo.get_beam_position())
    # print("going to 490 : ", hwo.distance.set_value(490))

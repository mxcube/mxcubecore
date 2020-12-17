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

import logging
import time

from mx3core.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
from mx3core.BaseHardwareObjects import HardwareObject

__author__ = "Vicente Rey"
__credits__ = ["SOLEIL"]
__version__ = "2.3."
__category__ = "General"


class PX1Pilatus(AbstractDetector, HardwareObject):
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

        self.exp_time_limits = None

        self.headers = {}

    def init(self):
        self.distance_motor_hwobj = self.get_object_by_role("detector_distance")
        self.devname = self.get_property("tangoname")

        self.state_chan = self.get_channel_object("state")
        self.state_chan.connect_signal("update", self.state_changed)

        self.threshold_chan = self.get_channel_object("threshold")
        self.threshold_chan.connect_signal("update", self.threshold_changed)

        self.set_energy_cmd = self.get_command_object("set_energy")
        self.set_header_cmd = self.get_command_object("set_header")

        exp_time_limits = self.get_property("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))

    def state_changed(self, state):
        self.current_state = state

    def threshold_changed(self, threshold):
        self.current_threshold = threshold

    def prepare_acquisition(self):
        pass

    def start_acquisition(self):
        # _dir_path = self.dcpars['fileinfo']['directory'].replace('RAW_DATA','PROCESSED_DATA')
        # chmod_dir(_dir_path)
        # write_goimg(_dir_path)
        pass

    def stop_acquisition(self):
        pass

    def get_state(self):
        return self.state_chan.get_value()

    def read_state(self):
        return str(self.get_state())

    def is_fault_state(self):
        return str(self.get_state()) == "FAULT"

    def get_threshold(self):
        return self.threshold_chan.get_value()

    def get_threshold_gain(self):
        return None

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_centre(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        try:
            if self.chan_beam_xy is not None:
                value = self.chan_beam_xy.get_value()
                beam_x = value[0]
                beam_y = value[1]
        except Exception:
            pass
        return beam_x, beam_y

    def get_manufacturer(self):
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
    def prepare_collection(self, dcpars):
        energy = dcpars["energy"]
        self.do_energy_calibration(energy)

        # osc_seq = dcpars['oscillation_sequence'][0]
        # file_pars = dcpars['fileinfo']

        # basedir = file_pars['directory']
        # prefix  =  "%s_%s_" % (file_pars['prefix'], file_pars['run_number'])
        #
        # first_img_no = osc_seq['start_image_number']
        # nb_frames =  osc_seq['number_of_images']
        # exp_time = osc_seq['exposure_time']
        #
        # fileformat =  "CBF"
        # trig_mode = "EXTERNAL_TRIGGER"
        # latency_time = 0.023
        #
        # logging.getLogger("HWR").debug(" Preparing detector (dev=%s) for data collection" % self.devname)
        #
        # logging.getLogger("HWR").debug("    /saving directory: %s" % basedir)
        # logging.getLogger("HWR").debug("    /prefix          : %s" % prefix)
        # logging.getLogger("HWR").debug("    /saving_format   : %s" % fileformat)
        # logging.getLogger("HWR").debug("    /trigger_mode    : %s" % trig_mode)
        # logging.getLogger("HWR").debug("    /acq_nb_frames   : %s" % nb_frames)
        # logging.getLogger("HWR").debug("    /acq_expo_time   : %s" % exp_time)
        # logging.getLogger("HWR").debug("    /latency_time    : %s" % latency_time)
        #
        # self.device.write_attribute('saving_mode', 'AUTO_FRAME')
        # self.device.write_attribute('saving_directory', basedir)
        # self.device.write_attribute('saving_prefix', prefix)
        # self.device.write_attribute('saving_format', fileformat)
        # self.device.write_attribute('saving_next_number', first_img_no)

        return True

    def start_collection(self):
        self.wait_energy_calibration()
        self.start_acquisition()

    def stop_collection(self):
        self.stop_acquisition()

    def set_image_headers(self, image_headers):
        for _header in image_headers:
            try:
                _str_header = _header[0] % _header[1]
            except Exception:
                _str_header = _header[0]

            self.set_header_cmd(_str_header)

    def do_energy_calibration(self, energy):
        energy = float(energy)
        logging.info("<PX1Pilatus> do_energy_calibration for %.4f KeV" % energy)

        PILATUS_THRESHOLD_MIN = 3774.0  # en eV
        ENERGY_CALIBRATION_MIN = 7.6  # en keV

        current_threshold = self.threshold_chan.get_value()

        energy_diff = energy - 2 * current_threshold / 1000.0

        if (
            current_threshold == PILATUS_THRESHOLD_MIN
            and energy < ENERGY_CALIBRATION_MIN
        ):
            logging.warning(
                "PX1Pilatus. Re-calibration of Pilatus detector not possible: THRESHOLD_MIN condition."
            )
            return False

        if energy_diff < (-0.08 * (2 * current_threshold / 1000.0)) or energy_diff > (
            0.05 * (2 * current_threshold / 1000.0)
        ):

            if self.read_state() != "STANDBY":
                logging.getLogger("user_level_log").error(
                    "Re-calibration of Pilatus detector not possible."
                )
                return False

            logging.info(
                "<PX1Pilatus> sending energy value of %5d KeV" % int(energy * 1000)
            )
            self.set_energy_cmd(int(energy * 1000))

            time.sleep(1)

            if self.read_state() != "STANDBY":
                logging.getLogger("user_level_log").info(
                    "Calibration of Pilatus detector in progress (takes about 1 minute)."
                )

    def wait_energy_calibration(self):
        _state = self.read_state()

        t0 = time.time()
        last_msg_time = 0
        while _state != "STANDBY":
            time.sleep(2)
            elapsed = time.time() - t0
            _state = self.read_state()
            if elapsed - last_msg_time > 10.0:
                logging.getLogger("user_level_log").info(
                    "   -  calibration in progress (elapsed time %s)." % elapsed
                )
                last_msg_time = elapsed
            logging.info(
                "    -  <PX1Pilatus>  waiting for energy calibration: %s" % _state
            )


def test_hwo(hwo):
    print(("Detector Distance is: %s " % hwo.distance.get_value()))
    print(("         state is: %s, %s" % (hwo.get_state(), type(hwo.get_state()))))
    print(("      is in fault: %s" % hwo.is_fault_state()))
    # print "going to 490 : ", hwo.distance.set_value(490)

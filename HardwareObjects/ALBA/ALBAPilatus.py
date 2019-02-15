#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import time

from AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject
from taurus import Device

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

        self.cmd_prepare_acq = None
        self.cmd_start_acq = None
        self.cmd_abort_acq = None
        self.cmd_reset_common_header = None
        self.cmd_reset_frame_headers = None
        self.cmd_set_image_header = None

        self.chan_saving_mode = None
        self.chan_saving_prefix = None
        self.chan_saving_directory = None
        self.chan_saving_format = None
        self.chan_saving_next_number = None
        self.chan_saving_header_delimiter = None

        self.chan_acq_nb_frames = None
        self.chan_acq_trigger_mode = None
        self.chan_acq_expo_time = None

        self.chan_latency_time = None

        self.chan_threshold = None
        self.chan_threshold_gain = None
        self.chan_cam_state = None

        self.chan_beam_x = None
        self.chan_beam_y = None
        self.chan_eugap = None

        self.distance_motor_hwobj = None

        self.default_distance = None
        self.default_distance_limits = None
        self.exp_time_limits = None
        self.device = None

        self.headers = {}

    def init(self):

        self.cmd_prepare_acq = self.getCommandObject('prepare_acq')
        self.cmd_start_acq = self.getCommandObject('start_acq')
        self.cmd_abort_acq = self.getCommandObject('abort_acq')
        self.cmd_reset_common_header = self.getCommandObject('reset_common_header')
        self.cmd_reset_frame_headers = self.getCommandObject('reset_frame_headers')
        self.cmd_set_image_header = self.getCommandObject('set_image_header')

        self.chan_saving_mode = self.getChannelObject('saving_mode')
        self.chan_saving_prefix = self.getChannelObject('saving_prefix')
        self.chan_saving_directory = self.getChannelObject('saving_directory')
        self.chan_saving_format = self.getChannelObject('saving_format')
        self.chan_saving_next_number = self.getChannelObject('saving_next_number')
        self.chan_saving_header_delimiter = self.getChannelObject(
            'saving_header_delimiter')

        self.chan_acq_nb_frames = self.getChannelObject('acq_nb_frames')
        self.chan_acq_trigger_mode = self.getChannelObject('acq_trigger_mode')
        self.chan_acq_expo_time = self.getChannelObject('acq_expo_time')

        self.chan_latency_time = self.getChannelObject('latency_time')

        self.chan_threshold = self.getChannelObject('threshold')
        self.chan_threshold_gain = self.getChannelObject('threshold_gain')
        self.chan_cam_state = self.getChannelObject('cam_state')

        self.distance_motor_hwobj = self.getObjectByRole("distance_motor")

        # TODO: set timeout via xml but for command?
        name = self.getProperty("taurusname")
        self.device = Device(name)
        self.device.set_timeout_millis(30000)

        exp_time_limits = self.getProperty("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))

        self.chan_beam_x = self.getChannelObject("beamx")
        self.chan_beam_y = self.getChannelObject("beamy")
        self.chan_eugap = self.getChannelObject("eugap")

    def start_acquisition(self):
        self.cmd_start_acq()

    def stop_acquisition(self):
        self.cmd_abort_acq()

    def get_distance(self):
        """Returns detector distance in mm"""
        if self.distance_motor_hwobj is not None:
            return float(self.distance_motor_hwobj.getPosition())
        else:
            return self.default_distance

    def move_distance(self, value):
        if self.distance_motor_hwobj is not None:
            self.distance_motor_hwobj.move(value)

    def wait_move_distance_done(self):
        self.distance_motor_hwobj.wait_end_of_move()

    def get_distance_limits(self):
        """Returns detector distance limits"""
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getLimits()
        else:
            return self.default_distance_limits

    def get_threshold(self):
        return self.chan_threshold.getValue()

    def get_threshold_gain(self):
        return self.chan_threshold_gain.getValue()

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_centre(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        try:
            beam_x = self.chan_beam_x.getValue()
            beam_y = self.chan_beam_y.getValue()
        except BaseException:
            pass
        return beam_x, beam_y

    def get_manufacturer(self):
        return self.getProperty("manufacturer")

    def get_model(self):
        return self.getProperty("model")

    def get_detector_type(self):
        return self.getProperty("type")

    def get_default_exposure_time(self):
        return self.getProperty("default_exposure_time")

    def get_minimum_exposure_time(self):
        return self.getProperty("minimum_exposure_time")

    def get_exposure_time_limits(self):
        """Returns exposure time limits as list with two floats"""
        return self.exp_time_limits

    def get_file_suffix(self):
        return self.getProperty("file_suffix")

    def get_pixel_size(self):
        return self.getProperty("px"), self.getProperty("py")

    def set_energy_threshold(self):
        try:
            current_energy = self.chan_eugap.getValue()
        except Exception as e:
            current_energy = 12.6

        det_energy = self.get_threshold()

        if round(current_energy, 6) < 7.538:
            current_energy = 7.538

        kev_diff = abs(det_energy - current_energy)

        if kev_diff > 1.2:
            logging.getLogger("HWR").debug("Setting detector energy_threshold: %s" %
                                           current_energy)

    def get_latency_time(self):
        return self.chan_latency_time.getValue()

    def wait_standby(self, timeout=300):
        t0 = time.time()
        while self.chan_cam_state == 'STANDBY':
            if time.time() - t0 > timeout:
                print "timeout waiting for Pilatus to be on STANDBY"
                return False
            time.sleep(0.1)
        return True

    def prepare_acquisition(self, dcpars):

        self.set_energy_threshold()

        osc_seq = dcpars['oscillation_sequence'][0]
        file_pars = dcpars['fileinfo']

        basedir = file_pars['directory']
        prefix = "%s_%s_" % (file_pars['prefix'], file_pars['run_number'])

        first_img_no = osc_seq['start_image_number']
        nb_frames = osc_seq['number_of_images']
        exp_time = osc_seq['exposure_time']

        fileformat = "CBF"
        trig_mode = "EXTERNAL_TRIGGER"

        logging.getLogger("HWR").debug(" Preparing detector for data collection")

        logging.getLogger("HWR").debug("    /saving directory: %s" % basedir)
        logging.getLogger("HWR").debug("    /prefix          : %s" % prefix)
        logging.getLogger("HWR").debug("    /saving_format   : %s" % fileformat)
        logging.getLogger("HWR").debug("    /trigger_mode    : %s" % trig_mode)
        logging.getLogger("HWR").debug("    /acq_nb_frames   : %s" % nb_frames)
        logging.getLogger("HWR").debug("    /acq_expo_time   : %s" %
                                       str(exp_time - self.latency_time))
        logging.getLogger("HWR").debug("    /latency_time    : %s" % self.latency_time)

        self.chan_saving_mode = 'AUTO_FRAME'
        self.chan_saving_directory = basedir
        self.chan_saving_prefix = prefix
        self.chan_saving_format = fileformat

        self.chan_acq_trigger_mode = trig_mode
        self.chan_acq_expo_time = exp_time - self.latency_time

        return True

    def prepare_collection(self, nb_frames, first_img_no):
        logging.getLogger("HWR").debug("Preparing collection")
        logging.getLogger("HWR").debug("# images = %s, first image number: %s" %
                                       (nb_frames, first_img_no))
        self.chan_acq_nb_frames = nb_frames
        self.chan_saving_next_number = first_img_no
        self.cmd_prepare_acq()
        return True

    def start_collection(self):
        self.start_acquisition()

    def stop_collection(self):
        self.stop_acquisition()

    def set_image_headers(self, image_headers, angle_info):

        nb_images = image_headers['nb_images']
        angle_inc = image_headers['Angle_increment']
        start_angle = image_headers['Start_angle']

        startangles_list = list()
        ang_start, ang_inc, spacing = angle_info
        for i in range(nb_images):
            startangles_list.append("%0.4f deg." % (ang_start + spacing * i))

        headers = list()
        for i, sa in enumerate(startangles_list):
            header = "_array_data.header_convention PILATUS_1.2\n" \
                "# Detector: PILATUS 6M, S/N 60-0108, Alba\n" \
                "# %s\n" \
                "# Pixel_size 172e-6 m x 172e-6 m\n" \
                "# Silicon sensor, thickness 0.000320 m\n" % time.strftime(
                    "%Y/%b/%d %T")

            # Acquisition values (headers dictionary) but overwrites start angle
            image_headers["Start_angle"] = sa
            for key, value in image_headers.iteritems():
                if key == 'nb_images':
                    continue
                header += "# %s %s\n" % (key, value)
            headers.append("%d : array_data/header_contents|%s;" % (i, header))

        self.chan_saving_header_delimiter = ["|", ";", ":"]
        self.cmd_reset_common_header()
        self.cmd_reset_frame_headers()
        self.cmd_set_image_header(headers)


def test_hwo(hwo):
    # Print channel values
    for chan in hwo.getChannels():
        print "%s = %s" % (chan.userName(), chan.getValue())

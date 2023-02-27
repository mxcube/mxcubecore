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

"""
[Name]
XalocPilatus

[Description]
Specific HwObj to interface the Pilatus2 6M detector

[Emitted signals]
- None
"""

from __future__ import print_function

import logging
import time

from datetime import datetime
from mxcubecore.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
#from mxcubecore.BaseHardwareObjects import HardwareObject
from taurus import Device

__credits__ = ["ALBA"]
__version__ = "3."
__category__ = "General"


ENERGY_CHANGE_LIMIT=1.2


class XalocPilatus(AbstractDetector):
    """Detector class. Contains all information about detector
       - states are 'OK', and 'BAD'
       - status is busy, exposing, ready, etc.
       - physical property is RH for pilatus, P for rayonix
    """

    def __init__(self, name):
        AbstractDetector.__init__(self, name)
        #HardwareObject.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocPilatus")
        self.cmd_prepare_acq = None
        self.cmd_start_acq = None
        self.cmd_abort_acq = None
        self.cmd_reset_common_header = None
        self.cmd_reset_frame_headers = None
        self.cmd_set_image_header = None

        self.cmd_set_threshold_gain = None

        self.chan_saving_mode = None
        self.chan_saving_prefix = None
        self.chan_saving_directory = None
        self.chan_saving_format = None
        self.chan_saving_next_number = None
        self.chan_saving_header_delimiter = None
        self.chan_saving_statistics = None

        self.chan_acq_nb_frames = None
        self.chan_acq_trigger_mode = None
        self.chan_acq_expo_time = None
        self.chan_acq_status = None
        self.chan_acq_status_fault_error = None

        self.chan_latency_time = None

        self.chan_energy = None
        self.chan_threshold = None
        self.chan_gain = None
        self.chan_cam_state = None

        self.chan_beam_x = None
        self.chan_beam_y = None
        self.chan_eugap = None

        self.default_distance = None
        self.default_distance_limits = None
        self.exp_time_limits = None
        self.device = None

        self.headers = {}

    def init(self):
        AbstractDetector.init(self)
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        
        self.cmd_prepare_acq = self.get_command_object('prepare_acq')
        self.cmd_start_acq = self.get_command_object('start_acq')
        self.cmd_abort_acq = self.get_command_object('abort_acq')
        self.cmd_reset = self.get_command_object('reset')
        self.cmd_reset_common_header = self.get_command_object('reset_common_header')
        self.cmd_reset_frame_headers = self.get_command_object('reset_frame_headers')
        self.cmd_set_image_header = self.get_command_object('set_image_header')

        self.cmd_set_threshold_gain = self.get_command_object('set_threshold_gain')

        self.chan_saving_mode = self.get_channel_object('saving_mode')
        self.chan_saving_prefix = self.get_channel_object('saving_prefix')
        self.chan_saving_directory = self.get_channel_object('saving_directory')
        self.chan_saving_format = self.get_channel_object('saving_format')
        self.chan_saving_next_number = self.get_channel_object('saving_next_number')
        self.chan_saving_header_delimiter = self.get_channel_object(
            'saving_header_delimiter')
        self.chan_saving_statistics = self.get_channel_object('saving_statistics')

        self.chan_acq_nb_frames = self.get_channel_object('acq_nb_frames')
        self.chan_acq_trigger_mode = self.get_channel_object('acq_trigger_mode')
        self.chan_acq_expo_time = self.get_channel_object('acq_expo_time')
        self.chan_acq_status = self.get_channel_object('acq_status')
        self.chan_acq_status_fault_error = self.get_channel_object(
            'acq_status_fault_error')

        self.chan_latency_time = self.get_channel_object('latency_time')

        self.chan_energy = self.get_channel_object('energy')
        self.chan_threshold = self.get_channel_object('threshold')
        self.chan_gain = self.get_channel_object('gain')
        self.chan_cam_state = self.get_channel_object('cam_state')


        # TODO: set timeout via xml but for command?
        name = self.get_property("taurusname")
        self.device = Device(name)
        self.device.set_timeout_millis(30000)

        exp_time_limits = self.get_property("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))

        self.chan_beam_x = self.get_channel_object("beamx")
        self.chan_beam_y = self.get_channel_object("beamy")
        self.chan_eugap = self.get_channel_object("eugap")

    def start_acquisition(self):
        self.cmd_start_acq()

    def stop_acquisition(self):
        self.cmd_abort_acq()
        self.cmd_reset()

    def get_distance(self):
        """Returns detector distance in mm"""
        if self._distance_motor_hwobj is not None:
            return float( self._distance_motor_hwobj.get_value() )
        else:
            return self.default_distance

    def move_distance(self, value):
        if self._distance_motor_hwobj is not None:
            self._distance_motor_hwobj.move(value)

    def wait_move_distance_done(self):
        self._distance_motor_hwobj.wait_end_of_move(timeout=1000)

    def wait_ready(self):
        self.wait_move_distance_done()
        self.wait_standby()

    def get_distance_limits(self):
        """Returns detector distance limits"""
        if self._distance_motor_hwobj is not None:
            return self._distance_motor_hwobj.get_limits()
        else:
            return self.default_distance_limits

    def get_energy(self):
        return self.chan_energy.get_value()

    def get_threshold(self):
        return self.chan_threshold.get_value()

    def get_gain(self):
        return self.chan_gain.get_value()

    def get_cam_state(self):
        return self.chan_cam_state.get_value()

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_position(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        try:
            beam_x = self.chan_beam_x.get_value()
            beam_y = self.chan_beam_y.get_value()
        except BaseException as e:
            self.logger.debug("Cannot load beam channels\n%s" % str(e))
        return beam_x, beam_y

    def get_manufacturer(self):
        return self.get_property("manufacturer")

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

    def _get_beamline_energy(self):
        try:
            beamline_energy = self.chan_eugap.get_value()
        except Exception as e:
            self.logger.debug("Error getting energy\n%s" % str(e))
            beamline_energy = 12.6
            self.logger.debug("Setting default energy = %s" % beamline_energy)
        return beamline_energy

    def set_gain(self, value):
        self.chan_gain.set_value(value)

    def arm(self):
        """
        Configure detector electronics.
        :return:
        """
        try:
            beamline_energy = self._get_beamline_energy()
            energy = self.get_energy()
            threshold = self.get_threshold()
            threshold_gain = self.get_gain()
            cam_state = self.get_cam_state()

            self.logger.debug("beamline energy (Eb): %s" % beamline_energy)
            self.logger.debug("energy_threshold (Eth): %s" % energy)
            self.logger.debug("current threshold gain: %s" % threshold_gain)

            if abs(energy - beamline_energy) > ENERGY_CHANGE_LIMIT:
                self.chan_energy.set_value(beamline_energy)
                logging.getLogger("user_level_log").info(
                    "Setting detector energy_threshold: %s" % beamline_energy)
                # wait until detector is configured
                # Wait for 3 secs to let time for iState to change
                time.sleep(3)
                if not self.wait_standby():
                    raise RuntimeError("Detector could not be configured!")
            else:
                logging.getLogger("user_level_log").info("Energy difference (Eth - Eb) is below the difference limit %s keV" % ENERGY_CHANGE_LIMIT)
                logging.getLogger("user_level_log").info("Detector energy threshold will remain unchanged (%s keV)" % energy)

#            if round(beamline_energy, 6) < 7.538:
#                beamline_energy = 7.538
#
#            kev_diff = abs(energy - beamline_energy)
#
#            if kev_diff > 1.2 or beamline_energy > 10.0:
#                if cam_state == 'STANDBY':
#                    if beamline_energy > 10.0:
#                        if threshold_gain != 'LOW':
#                            self.set_threshold_gain('LOW')
#                            self.logger.debug(
#                                "Setting threshold_gain to LOW for energy %s > 10keV" % str(round(kev_diff, 4)))
#                    else:
#                        self.chan_energy_threshold = beamline_energy
#                        self.logger.debug(
#                            "Setting detector energy_threshold: %s" % beamline_energy)
#                    # wait until detector is configured
#                    # Wait for 3 secs to let time for change
#                    time.sleep(3)
#                    if not self.wait_standby():
#                        raise RuntimeError("Detector could not be configured!")
#                else:
#                    msg = "Cannot set energy threshold, detector not in STANDBY"
#                    raise RuntimeError(msg)
        except Exception as e:
            self.logger.error("Exception when setting threshold to pilatus: %s" % str(e))

    def get_latency_time(self):
        return self.chan_latency_time.get_value()

    def wait_standby(self, timeout=300):
        if self.get_cam_state() != 'STANDBY':
            logging.getLogger("user_level_log").info("Waiting detector to be in STANDBY")
        t0 = time.time()
        while self.get_cam_state() != 'STANDBY':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus to be on STANDBY")
                return False
            time.sleep(1)
            self.logger.debug("Detector is %s" % self.get_cam_state())
        return True

    def wait_running(self, timestep=0.1, timeout=300):
        logging.getLogger("user_level_log").info("Waiting detector to be in RUNNING")
        t0 = time.time()
        while self.get_cam_state() != 'RUNNING':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus to be on RUNNING")
                return False
            time.sleep( timestep )
            self.logger.debug("Detector is %s" % self.get_cam_state())
        return True

    def prepare_acquisition(self, dcpars):

        self.arm()
        latency_time = self.get_latency_time()

        osc_seq = dcpars['oscillation_sequence'][0]
        file_pars = dcpars['fileinfo']

        basedir = file_pars['directory']
        prefix = "%s_%s_" % (file_pars['prefix'], file_pars['run_number'])

        #TODO: deprecated
        # first_img_no = osc_seq['start_image_number']
        nb_frames = osc_seq['number_of_images']
        exp_time = osc_seq['exposure_time']

        fileformat = "CBF"
        trig_mode = dcpars['detector_binning_mode'][0]

        self.logger.debug(" Preparing detector for data collection")

        self.logger.debug("    /saving directory: %s" % basedir)
        self.logger.debug("    /prefix          : %s" % prefix)
        self.logger.debug("    /saving_format   : %s" % fileformat)
        self.logger.debug("    /trigger_mode    : %s" % trig_mode)
        self.logger.debug("    /acq_nb_frames   : %s" % nb_frames)
        self.logger.debug("    /acq_expo_time   : %s" %
                                       str(exp_time - latency_time))
        self.logger.debug("    /latency_time    : %s" % latency_time)

        self.chan_saving_mode.set_value('AUTO_FRAME')
        self.chan_saving_directory.set_value(basedir)
        self.chan_saving_prefix.set_value(prefix)
        self.chan_saving_format.set_value(fileformat)

        self.chan_acq_trigger_mode.set_value(trig_mode)
        self.chan_acq_expo_time.set_value(exp_time - latency_time)

        return True

    def prepare_collection(self, nb_frames, first_img_no):
        self.logger.debug("Preparing collection")
        self.logger.debug("# images = %s, first image number: %s" %
                                       (nb_frames, first_img_no))
        self.chan_acq_nb_frames.set_value(nb_frames)
        self.chan_saving_next_number.set_value(first_img_no)
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
            header = "# Detector: PILATUS 6M, S/N 60-0108, Alba\n" \
                "# %s\n" \
                "# Pixel_size 172e-6 m x 172e-6 m\n" \
                "# Silicon sensor, thickness 0.000320 m\n" % datetime.now().strftime(
                        "%Y-%m-%dT%T.%f")[:-3]

            # Acquisition values (headers dictionary) but overwrites start angle
            image_headers["Start_angle"] = sa
            for key, value in image_headers.iteritems():
                if key == 'nb_images':
                    continue
                header += "# %s %s\n" % (key, value)
            headers.append("%d : array_data/header_convention|%s;" %  (i, "PILATUS_1.2")) 
            headers.append("%d : array_data/header_contents|%s;" % (i, header))

        self.chan_saving_header_delimiter.set_value(["|", ";", ":"])
        self.cmd_reset_common_header()
        self.cmd_reset_frame_headers()
        self.cmd_set_image_header(headers)

    def get_saving_statistics(self):
        values = self.chan_saving_statistics.get_value()
        if all(values):
            saving_speed, compression_speed, compression_ratio, incoming_speed = values
            comp_ratio = compression_speed / incoming_speed
            saving_ratio = saving_speed / (incoming_speed / compression_ratio)

            self.logger.debug("  compression ratio = %.4f" % comp_ratio)
            self.logger.debug("       saving ratio = %.4f" % saving_ratio)
            self.logger.debug("If comp_ratio < 1, increase the NbProcessingThread")
            self.logger.debug(
                "If saving_ratio < 1, increase the SavingMaxConcurrentWritingTask")
        else:
            self.logger.debug("No data available to evaluate the Pilatus/Lima performance")
            self.logger.debug("raw values --> %s" % values)

def test_hwo(hwo):
    for chan in hwo.getChannels():
        print("%s = %s" % (chan.userName(), chan.get_value()))

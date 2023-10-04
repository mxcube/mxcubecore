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
from mxcubecore import HardwareRepository as HWR

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
        self.cmd_stop_acq = None
        self.cmd_reset_common_header = None
        self.cmd_reset_frame_headers = None
        self.cmd_set_image_header = None

        #self.cmd_set_threshold_gain = None

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
        self.chan_lima_ready = None

        self.latency_time = None
        self.chan_latency_time = None

        self.chan_energy = None
        self.chan_threshold = None
        #self.chan_gain = None
        self.chan_cam_state = None
        self.cmd_cam_server = None

        self.chan_beam_x = None
        self.chan_beam_y = None
        self.chan_eugap = None

        self.default_distance = None
        self.default_distance_limits = None
        self.exp_time_limits = None
        self.device = None
        self.start_acq_cam_server = None
        
        self.headers = {}

    def init(self):
        AbstractDetector.init(self)
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))

        self.latency_time = self.get_property("latency_time")

        self.cmd_prepare_acq = self.get_command_object('prepare_acq')
        self.cmd_start_acq = self.get_command_object('start_acq')
        self.cmd_abort_acq = self.get_command_object('abort_acq')
        self.cmd_stop_acq = self.get_command_object('stop_acq')
        self.cmd_reset = self.get_command_object('reset')
        self.cmd_reset_common_header = self.get_command_object('reset_common_header')
        self.cmd_reset_frame_headers = self.get_command_object('reset_frame_headers')
        self.cmd_set_image_header = self.get_command_object('set_image_header')

        #self.cmd_set_threshold_gain = self.get_command_object('set_threshold_gain')

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
        self.chan_lima_ready = self.get_channel_object('lima_ready_for_next_acq')
        self.chan_latency_time = self.get_channel_object('latency_time')
    
        if self.latency_time == None:
            self.latency_time = self.chan_latency_time.get_value()
        else:
            self.chan_latency_time.set_value( self.latency_time )

        self.chan_energy = self.get_channel_object('energy')
        self.chan_threshold = self.get_channel_object('threshold')
        #self.chan_gain = self.get_channel_object('gain')
        self.chan_cam_state = self.get_channel_object('cam_state')
        self.cmd_cam_server = self.get_command_object('cmd_cam_server')

        # TODO: set timeout via xml but for command?
        name = self.get_property("taurusname")
        self.device = Device(name)
        self.device.set_timeout_millis(30000)

        exp_time_limits = self.get_property("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))
        self.start_acq_cam_server = self.get_property("start_acq_cam_server")

        self.chan_beam_x = self.get_channel_object("beamx")
        self.chan_beam_y = self.get_channel_object("beamy")
        self.chan_eugap = self.get_channel_object("eugap")

    def start_acquisition(self):
        if self.start_acq_cam_server is True:
            #TODO format the number of digits correctly
            first_file_name = self.chan_saving_prefix.get_value() + \
                "%04d" % self.chan_saving_next_number.get_value() + \
                "." + self.chan_saving_format.get_value().lower()
            self.cmd_cam_server("ExtTrigger %s" % first_file_name)
        else:
            self.cmd_start_acq()

    def stop_acquisition(self):
        self.logger.debug("Stopping detector and resetting it")
        if self.start_acq_cam_server is True:
            self.cmd_cam_server("k")
            self.wait_not_running()
            self.chan_energy.set_value( self._get_beamline_energy() )
        else:
            #self.cmd_stop_acq()
            self.cmd_abort_acq()
            self.wait_not_running()
            time.sleep(0.1)
            self.cmd_reset()

    def get_radius(self, distance=None):
        """Get distance from the beam position to the nearest detector edge.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector radius [mm]
        """
        try:
            distance = distance or self._distance_motor_hwobj.get_value()
        except AttributeError:
            raise RuntimeError("Cannot calculate radius, distance unknown")

        beam_x, beam_y = self.get_beam_position(distance)
        pixel_x, pixel_y = self.get_pixel_size()
        rrx = min(self.get_width() - beam_x, beam_x) * pixel_x
        rry = min(self.get_height() - beam_y, beam_y) * pixel_y
        radius = min(rrx, rry)

        return radius
        

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
        self._distance_motor_hwobj.wait_ready(1000)
        #self._distance_motor_hwobj.wait_end_of_move(timeout=1000) # wait_end_of_nove does not work!

    def wait_ready(self):
        self.wait_move_distance_done()
        self.wait_standby()

    def wait_lima_ready(self):
        self.wait_move_distance_done()
        self.wait_lima_ready_for_next_acq()

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

    #def get_gain(self):
        #return self.chan_gain.get_value()

    def get_cam_state(self):
        return self.chan_cam_state.force_get_value()

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        """
           Returns beam center coordinates
           TODO: update values according to distance, see XALOC modules for the calculation and calibration
        """
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

    #def set_gain(self, value):
        #self.chan_gain.set_value(value)

    def arm(self):
        """
        Configure detector electronics.
        :return:
        """
        self.logger.debug("Arming the detector")
        try:
            beamline_energy = self._get_beamline_energy()
            energy = self.get_energy()
            threshold = self.get_threshold()
            #threshold_gain = self.get_gain()
            cam_state = self.get_cam_state()

            self.logger.debug("beamline energy (Eb): %s" % beamline_energy)
            self.logger.debug("energy_threshold (Eth): %s" % energy)
            #self.logger.debug("current threshold gain: %s" % threshold_gain)

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
        if self.latency_time != None:
            return self.latency_time
        return self.chan_latency_time.get_value()

    def wait_standby(self, timestep = 0.1, timeout=300):
        standby = self.get_cam_state() 
        if standby != 'STANDBY':
            self.logger.debug("Waiting detector to be in STANDBY")
        t0 = time.time()
        while standby != 'STANDBY' and standby != 'ERROR':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus to be on STANDBY")
                return False
            time.sleep(timestep)
            standby = self.get_cam_state() 
            #self.logger.debug("Detector is %s" % self.get_cam_state())
        if standby == 'STANDBY': return True
        return False 

    def wait_lima_ready_for_next_acq(self, timeout=300):
        lima_ready = self.chan_lima_ready.get_value() 
        if lima_ready != True:
            logging.getLogger("").info("Waiting detector lima to be ready for next image")
        t0 = time.time()
        while lima_ready != True and HWR.beamline.collect._collecting and self.get_cam_state() != 'ERROR':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus lima to be ready for next image")
                return False
            time.sleep(0.1)
            lima_ready = self.chan_lima_ready.get_value() 
            #self.logger.debug("Detector lima ready for next image is %s" %  lima_ready )
        return True

    def wait_running(self, timestep=0.1, timeout=300):
        self.logger.debug("Waiting detector to be in RUNNING")
        t0 = time.time()
        while self.get_cam_state() != 'RUNNING':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus to be inn RUNNING state")
                return False
            time.sleep( timestep )
            #self.logger.debug("Detector is %s" % self.get_cam_state())
        return True

    def wait_not_running(self, timestep=0.1, timeout=300):
        self.logger.debug("Waiting detector to stop RUNNING")
        t0 = time.time()
        self.logger.debug("wait_not_running: Detector is %s" % self.get_cam_state())
        while self.get_cam_state() == 'RUNNING':
            if time.time() - t0 > timeout:
                self.logger.debug("timeout waiting for Pilatus to stop RUNNING")
                return False
            time.sleep( timestep )
            #self.logger.debug("Detector is %s" % self.get_cam_state())
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

        return True

    def set_exposure_time(exp_period):
        self.chan_acq_expo_time.set_value(exp_period - latency_time)

    def prepare_collection(self, nb_frames, first_img_no, exp_time):
        self.logger.debug("Preparing collection")
        self.logger.debug("# images = %s, first image number: %s, exp_time %.4f" %
                                       (nb_frames, first_img_no, exp_time)
                          )
        self.chan_acq_nb_frames.set_value(nb_frames)
        self.chan_saving_next_number.set_value(first_img_no)
        self.chan_acq_expo_time.set_value(exp_time)
        self.cmd_prepare_acq()
        return True

    def start_collection(self):
        self.start_acquisition()

    def stop_collection(self):
        self.stop_acquisition()

    def set_image_headers(self, image_headers, angle_info):
        """
            Prepares headers both in lima as well as the camserver
            TODO: use start_acq_cam_server to set the appropriate header
        """
        
        nb_images = image_headers['nb_images']
        angle_inc = image_headers['Angle_increment']
        start_angle = image_headers['Start_angle']

        ang_start, ang_inc, spacing = angle_info

        #Set the camserver headings in case lima is not used
        self.cmd_cam_server("MXsettings Start_angle %s" % image_headers["Start_angle"].split()[0]  )
        self.cmd_cam_server("MXsettings Angle_increment %s" % image_headers["Angle_increment"].split()[0] )
        self.cmd_cam_server("MXsettings Kappa %s" % image_headers["Kappa"].split()[0] )
        self.cmd_cam_server("MXsettings Phi %s" % image_headers["Phi"].split()[0] )
        self.cmd_cam_server("MXsettings Flux %s" % image_headers["Flux"].split()[0]  )
        self.cmd_cam_server("MXsettings Wavelength %s" % image_headers["Wavelength"].split()[0] )
        self.cmd_cam_server("MXsettings Filter_transmission %s" % image_headers["Filter_transmission"].split()[0]  )
        self.cmd_cam_server("MXsettings Detector_distance %s" % image_headers["Detector_distance"].split()[0]  )
        self.cmd_cam_server("MXsettings Polarization %s" % image_headers["Polarization"].split()[0]  )
        self.cmd_cam_server("MXsettings Detector_2theta %s" % image_headers["Detector_2theta"].split()[0]  )
        self.cmd_cam_server("MXsettings Beam_xy %s" % image_headers["Beam_xy"].split("pixels")[0]  )
        self.cmd_cam_server("MXsettings Detector_Voffset %s" % image_headers["Detector_Voffset"].split()[0]  )
        self.cmd_cam_server("MXsettings Oscillation_axis %s" % image_headers["Oscillation_axis"]  )

        startangles_list = list()
        for i in range(nb_images):
            startangles_list.append("%0.4f deg." % (ang_start + spacing * i))

        headers = list()
        for i, sa in enumerate(startangles_list):
            header = "# Detector: PILATUS3X 6M, S/N 60-0140, XALOC, Alba\n" \
                "# %s\n" \
                "# Pixel_size 172e-6 m x 172e-6 m\n" \
                "# Silicon sensor, thickness 0.001 m\n" % datetime.now().strftime(
                        "%Y-%m-%dT%T.%f")[:-3]

            # Acquisition values (headers dictionary) but overwrites start angle
            image_headers["Start_angle"] = sa
            for key, value in image_headers.iteritems():
                if key == 'nb_images':
                    continue
                header += "# %s %s\n" % (key, value)
            headers.append("%d : array_data/header_convention|%s;" %  (i, "PILATUS_1.2")) 
            headers.append("%d : array_data/header_contents|%s;" % (i, header))

        #self.logger.debug("  saving header delimiters %s" % ["|", ";", ":"])
        self.chan_saving_header_delimiter.set_value(["|", ";", ":"])
        #self.logger.debug("  reset_common_header" )
        self.cmd_reset_common_header()
        #self.logger.debug("  reset_frame_headers" )
        self.cmd_reset_frame_headers()
        #self.logger.debug("  set_image_header %s" % headers)
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

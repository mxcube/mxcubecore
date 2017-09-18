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
from AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject

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
        
        self.exp_time_limits = None

    def init(self):
        self.distance_motor_hwobj = self.getObjectByRole("distance_motor")
        self.devname = self.getProperty("tangoname")
        self.devspecific = self.getProperty("tangospecific")

        exp_time_limits = self.getProperty("exposure_limits")
        self.exp_time_limits = map(float, exp_time_limits.strip().split(","))

        self.device = DeviceProxy(self.devname)
        self.device.set_timeout_millis(30000)

        self.device_specific = DeviceProxy(self.devspecific)

    def prepare_acquisition(self):
        self.device.prepareAcq()

    def start_acquisition(self):
        self.device.startAcq()

    def stop_acquisition(self):
        self.device.stopAcq()

    def get_distance(self):
        """Returns detector distance in mm"""
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getPosition()
        else:
            return self.default_distance

    def move_distance(self,value):
        if self.distance_motor_hwobj is not None:
            self.distance_motor_hwobj.move(value)

    def get_distance_limits(self):
        """Returns detector distance limits"""
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getLimits()
        else:
            return self.default_distance_limits

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return True

    def get_beam_centre(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        try:
            if self.chan_beam_xy is not None:
                value = self.chan_beam_xy.getValue()
                beam_x = value[0]
                beam_y = value[1]
        except:
            pass
        return beam_x, beam_y

    def get_manufacturer(self):
        return self.getProperty("manufacturer")
        return "Dectris"

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

    # methods for data collection    
    def prepare_collection(self, dcpars):

        osc_seq = dcpars['oscillation_sequence'][0]
        file_pars = dcpars['fileinfo']

        basedir = file_pars['directory']
        prefix  =  file_pars['prefix']

        first_img_no = osc_seq['start_image_number']
        nb_frames =  osc_seq['number_of_images']
        exp_time = osc_seq['exposure_time']

        fileformat =  "CBF"
        trig_mode = "EXTERNAL_TRIGGER"
        latency_time = 0.023

        self.device.write_attribute('saving_mode', 'AUTO_FRAME')

        self.device.write_attribute('saving_directory', basedir)
        self.device.write_attribute('saving_prefix', prefix)
        self.device.write_attribute('saving_format', fileformat)

        # set ROI and header in limaserver
        #  TODO

        # set first image - TODO check (is this in specific??)
        self.device_specific.write_attribute('nb_first_image', first_img_no)

        TrigList = ['INTERNAL_TRIGGER'
            ,'EXTERNAL_TRIGGER'
            ,'EXTERNAL_TRIGGER_MULTI'
            ,'EXTERNAL_GATE'
            ,'EXTERNAL_START_STOP']

        self.device.write_attribute('acq_trigger_mode', trig_mode)
        self.device.write_attribute('acq_nb_frames', nb_frames)
        self.device.write_attribute('acq_expo_time', exp_time)
        self.device.write_attribute('latency_time', latency_time)
        self.device.prepareAcq()

        return True

    def start_collection(self):
        self.start_acquisition()

    def stop_collection(self):
        self.stop_acquisition()


def test_hwo(hwo):
    print "Detector Distance is: ", hwo.get_distance()
    #print "going to 490 : ", hwo.move_distance(490)


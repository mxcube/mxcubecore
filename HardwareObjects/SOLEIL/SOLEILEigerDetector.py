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
[Name] : EigerDetector(Equipment)

[Description] : Describes generic detector 

[Channels] :

[Commands] :

[Emited signals] :

[Properties] : 

[Hardware Objects]      
-------------------------------------------------------------------------------
| name                       | signals             | functions
|------------------------------------------------------------------------------
| self.distance_motor_hwobj  |                     | getPosition()
-------------------------------------------------------------------------------
"""

import logging 
from AbstractDetector import AbstractDetector

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import HardwareObject

__author__ = "Bixente Rey"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2"

from eigerclient import DEigerClient

class eiger_client_dectris(DEigerClient):
    def __init__(self, host, port):
        DEigerClient.__init__(self, host=host, port=port)

class SOLEILEigerDetector(AbstractDetector, HardwareObject):
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
        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)

        self.beam_centre_x = None
        self.beam_centre_y = None

    def init(self):
        """
        Descript. :
        """
        
        logging.getLogger("HWR").debug("Eiger access: socket")

        host = self.getProperty("host")
        port = self.getProperty("port")

        if None in (host,port):
            logging.getLogger("HWR").error("Eiger configuration is not complete. Needs host and port")
            self.client =  None
        else:
            self.host = host
            self.port = port
            logging.getLogger("HWR").debug("Eiger configured in {o.host}:{o.port}".format(o=self))
            self.client =  eiger_client_dectris(self.host, self.port)
                
        if self.get_compression() != 'bslz4':
            self.set_compression('bslz4')

        # self.distance_motor_hwobj = self.getObjectByRole("distance_motor")
        # self.collect_name = self.getProperty("collectName")
        # self.shutter_name = self.getProperty("shutterName")
 
    def start_collection(self, dc):
        
        if self.scan_axis == 'vertical':
            self.set_nimages_per_file(self.number_of_rows)
            self.set_ntrigger(self.number_of_columns)
            self.set_nimages(self.number_of_rows)
        else:
            self.set_nimages_per_file(self.number_of_columns)
            self.set_ntrigger(self.number_of_rows)
            self.set_nimages(self.number_of_columns)

        self.set_frame_time(self.frame_time)
        self.set_count_time(self.count_time)
        self.set_name_pattern(self.name_pattern)
        self.set_omega(self.scan_start_angle)

        if self.angle_per_frame <= 0.01:
            self.set_omega_increment(0)
        else:
            self.set_omega_increment(self.angle_per_frame)

        self.set_image_nr_start(self.image_nr_start)
        self.set_detector_distance(self.beam_centre.get_detector_distance() / 1000.)

        return self.arm()

    def set_beam_centre(self, beam_centre):
        cent_x, cent_y = beam_centre
 
        if None not in [cent_x, cent_y]:
            if cent_x != self.beam_centre_x
                self.set_beam_center_x(cent_x)
                self.beam_centre_x = cent_x

            if cent_y != self.beam_centre_y
                self.set_beam_center_y(cent_y)
                self.beam_centre_y = cent_y

    def get_pixel_size(self):
        # not implemented yet
        return 75e-6, 75e-6

    def get_beam_centre(self):
        """
        Descrip. :
        """
        beam_x = 0
        beam_y = 0
        if self.chan_beam_xy is not None:
            value = self.chan_beam_xy.getValue()
            beam_x = value[0]
            beam_y = value[1]
        return beam_x, beam_y

def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    detector = hwr.getHardwareObject("/eiger")

if __name__ == '__main__':
   test()

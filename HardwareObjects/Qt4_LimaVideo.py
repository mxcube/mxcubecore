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
Qt4_LimaVideo

[Description]
HwObj used to grab images via LImA library or Lima Tango server.

[Configuration]
See example below.  To select between "Library" or "Tango" simply
use and configure the field <address> (for Library) 
or <tangoname> (for Tango)
in the XML file.


Example Hardware Object XML file :
==================================
<device class="Qt4_LimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <address>84.89.227.6</address>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</device>
"""
import os
import time
import logging
import struct

from GenericVideoDevice import GenericVideoDevice

try:
    from Lima import Core
except:
    pass

try:
    from Lima import Prosilica
except ImportError, e:
    pass

try:
    from Lima import Basler
except ImportError, e:
    pass

class Qt4_LimaVideo(GenericVideoDevice):
    """
    Descript. : 
    """
    def __init__(self, name):
        """
        Descript. :
        """
        GenericVideoDevice.__init__(self, name)

        self.cam_address = None

        # LIMA access
        self.camera = None
        self.interface = None
        self.control = None
        self.video = None 

    def init(self):
        self.useqt = True
        self.cam_address = self.getProperty("address")
        self.cam_type = self.getProperty("type").lower()

        if self.cam_type == 'prosilica':
            self.camera = Prosilica.Camera(self.cam_address)
            self.interface = Prosilica.Interface(self.camera) 
        elif self.cam_type == 'basler':
            logging.getLogger("HWR").info("Connecting to camera with address %s" % self.cam_address)
            self.camera = Basler.Camera(self.cam_address)
            self.interface = Basler.Interface(self.camera)
 
        self.control = Core.CtControl(self.interface)
        self.video = self.control.video()

        GenericVideoDevice.init(self)

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            self.video.setMode(Core.YUV422)
        elif cam_encoding == "y8":
            self.video.setMode(Core.Y8)

        GenericVideoDevice.set_cam_encoding(self,cam_encoding)

    """ Overloading of GenericVideoDevice methods """
    def get_image_dimensions(self):
        if self.cam_type == 'prosilica':
            return list(self.camera.getMaxWidthHeight())
        elif self.cam_type == 'basler':
            width = self.camera.getRoi().getSize().getWidth()
            height = self.camera.getRoi().getSize().getHeight()
            return [width, height]
        else:
            return [None,None]

    def get_image(self):
        image = self.video.getLastImage()
        if image.frameNumber() > -1:
            raw_buffer = image.buffer()
            return raw_buffer, image.width(), image.height()
        else:
            return None, None, None 

    def get_gain(self):
        value = self.video.getGain()
        return value

    def set_gain(self, gain_value):
        self.video.setGain(gain_value)

    def get_exposure_time(self):
        return self.video.getExposure()

    def set_exposure_time(self, exposure_time_value):
        self.video.setExposure(exposure_time_value)

    def get_video_live(self):
        return self.video.getLive()

    def set_video_live(self, flag):
        if flag is True:
            self.video.startLive()
        else:
            self.video.stopLive()

    """ END Overloading of GenericVideoDevice methods """

def test_hwo(hwo):
    print "Image dimensions: ", hwo.get_image_dimensions()
    print "Live Mode: ", hwo.get_video_live()

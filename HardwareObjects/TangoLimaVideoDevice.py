#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
TangoLimaVideoDevice

[Note]
This class was previously called QtTangoLimaVideo.  It was changed to
TangoLimaVideoDevice as it can be used now in Qt4(Qt5) environment or
without it.
The property <useqt>False</useqt> in the xml configuration file will inhibit
the use of qt.

The Hardware Object will poll for images at regular interval
(set by property <interval>value-in-msecs</interval>
For every image received a signal "imageReceived" is emitted. The content of the
information emitted varies:
- When qt is used:
   a "qimage" is delivered as parameter with the signal

- When qt is not used  (for web applications):
   three values are sent with the signal
     val1:  string with jpeg encoding of the image
     val2:  width (pixels) of the image
     val3:  height (pixels) of the image

   (web, non-qt encoding, has been validated for Prosilica cameras
     but in principle other cameras could also adopt the same mechanism)

[Description]
HwObj used to grab images via Tango Lima device server
If you want to access the Lima Library directly you may consider using
the LimaVideoDevice module instead

[Configuration]
Example Hardware Object XML file :
==================================
<device class="QtLimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <tangoname>bl13/eh/lima_oav</tangoname>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</device>
"""
from __future__ import print_function
import struct
import numpy as np

import PyTango


class TangoLimaVideoDevice(AbstractVideoDevice):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractVideoDevice.__init__(self, name)
        self.device = None

    def init(self):
        """
        Descript. :
        """

        tangoname = self.get_property("tangoname")
        endian = self.get_property("endian")

        if endian in ["small", "Small", "Little", "little"]:
            self.header_fmt = "<IHHqiiHHHH"
        else:
            self.header_fmt = ">IHHqiiHHHH"

        self.header_size = struct.calcsize(self.header_fmt)

        self.device = PyTango.DeviceProxy(tangoname)
        self.device.ping()

        AbstractVideoDevice.init(self)

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            self.device.video_mode = "YUV422"
        elif cam_encoding == "y8":
            self.device.video_mode = "Y8"

        AbstractVideoDevice.set_cam_encoding(self, cam_encoding)

    """ Overloading of AbstractVideoDevice methods """

    def get_image_dimensions(self):
        return [self.device.image_width, self.device.image_height]

    def get_image(self):
        img_data = self.device.video_last_image

        if img_data[0] == "VIDEO_IMAGE":
            raw_fmt = img_data[1][: self.header_size]
            raw_buffer = np.fromstring(img_data[1][self.header_size :], np.uint16)
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
                self.header_fmt, img_data[1][: self.header_size]
            )
            return raw_buffer, width, height
        else:
            return None, 0, 0

    def get_gain(self):
        if self.get_cam_type() == "basler":
            value = self.device.video_gain
            return value

    def set_gain(self, gain_value):
        if self.get_cam_type() == "basler":
            self.device.video_gain = gain_value
            return

    def get_exposure_time(self):
        if self.get_cam_type() == "basler":
            return self.device.video_exposure

    def set_exposure_time(self, exposure_time_value):
        if self.get_cam_type() == "basler":
            self.device.video_exposure = exposure_time_value

    def get_video_live(self):
        return self.device.video_live

    def set_video_live(self, flag):
        self.device.video_live = flag

    """ END Overloading of AbstractVideoDevice methods """


def test_hwo(hwo):
    print("Image dimensions: ", hwo.get_image_dimensions())
    print("Live Mode: ", hwo.get_video_live())

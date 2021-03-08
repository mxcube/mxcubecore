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

"""
[Name]
Qt4_TangoLimaVideo

[Description]
HwObj used to grab images via Tango Lima device server
If you want to access the Lima Library directly you may consider using
the Qt4_LimaVideo module instead

[Configuration]
Example Hardware Object XML file :
==================================
<device class="Qt4_LimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <tangoname>bl13/eh/lima_oav</tangoname>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</device>
"""

import os
import time
import gevent
import logging
import struct
import numpy as np

from GenericVideoDevice import GenericVideoDevice
from camera import camera

from gui.utils.qt_import import QImage, QPixmap


class PX2Video(GenericVideoDevice, camera):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        GenericVideoDevice.__init__(self, name)
        camera.__init__(self)
        self.log = logging.getLogger("user_level_log")
        self.device = name
        self.camera = camera()
        self.width = 1360
        self.height = 1024

    def init(self):
        """
        Descript. :
        """
        # tangoname = self.get_property("tangoname")

        self.log.info("PX2Video init")

        self.device = self.prosilica

        GenericVideoDevice.init(self)

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            self.device.video_mode = "YUV422"
        elif cam_encoding == "y8":
            self.device.video_mode = "Y8"

        GenericVideoDevice.set_cam_encoding(self, cam_encoding)

    def get_video_live(self):
        return True

    def set_video_live(self, flag):
        return
        self.device.video_live = flag

    def get_image_dimensions(self):
        return self.camera.get_image_dimensions()

    def get_image(self):
        return self.camera.get_image(), self.width, self.height

    def get_new_image(self):
        """
        Descript. :
        """
        raw_buffer, width, height = self.get_image()

        if raw_buffer is not None:
            qimage = QImage(raw_buffer, width, height, QImage.Format_RGB888)

            qpixmap = QPixmap(qimage)
            self.emit("imageReceived", qpixmap)
            return qimage

    # def get_jpg_image(self):
    # image = self.camera.get_image()

    # self.emit("imageReceived", qpixmap)
    # return qimage

    def do_image_polling(self, sleep_time=1):
        """
        Descript. :
        """
        while self.get_video_live() == True:
            self.get_new_image()
            gevent.sleep(1)

    """ END Overloading of GenericVideoDevice methods """


def test_hwo(hwo):
    print("Image dimensions: ", hwo.get_image_dimensions())
    print("Live Mode: ", hwo.get_video_live())

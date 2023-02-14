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
XalocQtTangoLimaVideo

[Description]
HwObj used to grab images via Tango LImA library or Lima Tango server, based on QtTangoLimaVideo.

[Configuration]
See example below.  To select between "Library" or "Tango" simply
use and configure the field <address> (for Library)
or <tangoname> (for Tango)
in the XML file.


Example Hardware Object XML file :
==================================
<device class="QtLimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <address>84.89.227.6</address>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</device>
"""

__credits__ = ["ALBA"]
__version__ = "3."
__category__ = "General"

import sys
import numpy as np

import logging

from mxcubecore.HardwareObjects.QtTangoLimaVideo import QtTangoLimaVideo
from mxcubecore.HardwareObjects.abstract.AbstractVideoDevice import (
    AbstractVideoDevice,
)

try:
    import cv2
except:
    pass

module_names = ["qt", "PyQt5", "PyQt4"]

if any(mod in sys.modules for mod in module_names):
    USEQT = True
    try:
        from PyQt5.QtGui import QImage, QPixmap
    except ImportError:
        from PyQt4.QtGui import QImage, QPixmap
else:
    USEQT = False
    from PIL import Image

class XalocQtTangoLimaVideo(QtTangoLimaVideo):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        self.logger = logging.getLogger("HWR")
        self.logger.debug("XalocQtTangoLimaVideo.__init__()")
        QtTangoLimaVideo.__init__(self, name)
        self.align_mode = None

    def init(self):
        QtTangoLimaVideo.init(self)
        # TODO: Sometimes, the error Can't set live mode if an acquisition is running appears. The bzoom DS needs to be restarted in that case
        #    check refresh_camera method of the camera / sample_view
        self.align_mode = False

    def set_cam_encoding(self, cam_encoding):
        self.logger.debug("XalocQtTangoLimaVideo set_cam_encoding")
        if cam_encoding == "yuv422p":
            self.device.video_mode = "YUV422"
        if cam_encoding == "rgb24":
            self.device.video_mode = "RGB24"
        elif cam_encoding == "y8":
            self.device.video_mode = "Y8"
        elif cam_encoding.lower() == "bayer_rg16":
            self.device.video_mode = "BAYER_RG16"

        self.logger.debug(
            "%s: using %s encoding" %
            (self.name, cam_encoding)
        )

        AbstractVideoDevice.set_cam_encoding(self, cam_encoding)

        self.logger.debug(
            "%s: using %s encoding" %
            (self.name, cam_encoding)
        )

        
    def get_new_image(self):
        """
        Descript. :
        """
        raw_buffer, width, height = self.get_image()

        # self.cam_type is bzoom

        if raw_buffer is not None and raw_buffer.any():
            if self.cam_type == "basler":
                raw_buffer = self.decoder(raw_buffer)
                if self.align_mode:
                    raw_buffer = cv2.applyColorMap(raw_buffer, cv2.COLORMAP_JET)

                qimage = QImage(raw_buffer, width, height,
                                width * 3,
                                QImage.Format_RGB888)
            else:
                raw_buffer = self.bgr_2_rgb(raw_buffer)
                if self.align_mode:
                    raw_buffer = cv2.applyColorMap(cv2.bitwise_not(raw_buffer), cv2.COLORMAP_JET)

                qimage = QImage(raw_buffer, width, height,
                                QImage.Format_RGB888)

            if self.cam_mirror is not None:
                qimage = qimage.mirrored(self.cam_mirror[0], self.cam_mirror[1])     

            if self.scale != 1:
               dims = self.get_image_dimensions()  #  should be already scaled
               qimage = qimage.scaled(QSize(dims[0], dims[1]))

            qpixmap = QPixmap(qimage)
            self.emit("imageReceived", qpixmap)
            return qimage.copy()

    def bgr_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        raw_dims = self.get_raw_image_size()
        image.resize(raw_dims[1], raw_dims[0], 3)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

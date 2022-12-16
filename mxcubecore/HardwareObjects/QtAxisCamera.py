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

import time
import Image
import base64
import urllib2

import numpy as np

from cStringIO import StringIO
from PIL.ImageQt import ImageQt

from mxcubecore.utils import qt_import
from mxcubecore.HardwareObjects.abstract.AbstractVideoDevice import (
    AbstractVideoDevice,
)

"""
Hardare objects allows to access Axis camera jpg frames via direct http requests.

Example xml:
<device class="AxisCamera">
   <interval>1000</interval>
   <address>ADDRESS_OF_THE_CAMERA/axis-cgi/jpg/image.cgi</address>
   <user>USER</user>
   <password>PASSWORD</password>
   <image_size>(600, 480)</image_size>
</device>
"""


class QtAxisCamera(AbstractVideoDevice):
    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)

    def init(self):
        self.image_dimensions = [352, 288]
        self.request = urllib2.Request(self.get_property("address"))
        base64string = base64.b64encode(
            "%s:%s" % (self.get_property("user"), self.get_property("password"))
        )
        self.request.add_header("Authorization", "Basic %s" % base64string)
        self.qpixmap = QPixmap()
        self.set_is_ready(True)

        AbstractVideoDevice.init(self)

        self.set_video_live(False)

    def get_new_image(self):
        result = urllib2.urlopen(self.request)
        self.qpixmap.loadFromData(result.read(), "JPG")
        self.emit("imageReceived", self.qpixmap)

    def save_snapshot(self, filename, image_type="PNG"):
        qimage = qt_import.QImage(self.image)
        qimage.save(filename, image_type)

    def get_snapshot(self, bw=None, return_as_array=None):
        qimage = self.qimage
        if return_as_array:
            qimage = qimage.convertToFormat(4)
            ptr = qimage.bits()
            ptr.setsize(qimage.byteCount())

            image_array = np.array(ptr).reshape(qimage.height(), qimage.width(), 4)
            if bw:
                return np.dot(image_array[..., :3], [0.299, 0.587, 0.144])
            else:
                return image_array
        else:
            if bw:
                return qimage.convertToFormat(qt_import.QImage.Format_Mono)
            else:
                return qimage

    def get_raw_image_size(self):
        return list(self.image_dimensions)

    def do_image_polling(self, sleep_time):
        while True:
            if self.get_video_live():
                self.get_new_image()
            time.sleep(sleep_time)

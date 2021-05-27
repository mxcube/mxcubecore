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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import os
import time
import numpy as np

from mxcubecore.utils.qt_import import QPainter, QPixmap, QPen, QBrush, QImage, Qt
from mxcubecore.HardwareObjects.abstract.AbstractVideoDevice import (
    AbstractVideoDevice,
)


class QtVideoMockup(AbstractVideoDevice):
    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)
        self.force_update = None
        self.image_type = None
        self.image = None

    def init(self):
        default_image_path = os.path.dirname(os.path.abspath(__file__)) + "/sample.jpg"
        image_path = self.get_property("file_name", default_image_path)

        self.image = QPixmap(image_path)
        self.image_dimensions = (self.image.width(), self.image.height())
        self.painter = QPainter(self.image)

        custom_pen = QPen(Qt.SolidLine)
        custom_pen.setColor(Qt.black)
        custom_pen.setWidth(1)
        self.painter.setPen(custom_pen)

        custom_brush = QBrush(Qt.SolidPattern)
        custom_brush.setColor(Qt.lightGray)
        self.painter.setBrush(custom_brush)

        self.set_is_ready(True)
        AbstractVideoDevice.init(self)

    def get_new_image(self):
        self.painter.drawRect(self.image.width() - 75, self.image.height() - 30, 70, 20)
        self.painter.drawText(
            self.image.width() - 70, self.image.height() - 15, time.strftime("%H:%M:%S")
        )
        self.emit("imageReceived", self.image)

    def save_snapshot(self, filename, image_type="PNG"):
        qimage = QImage(self.image)
        qimage.save(filename, image_type)

    def get_snapshot(self, bw=None, return_as_array=None):
        qimage = QImage(self.image)
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
                return qimage.convertToFormat(QImage.Format_Mono)
            else:
                return qimage

    def get_contrast(self):
        return 34

    def set_contrast(self, contrast_value):
        return

    def get_brightness(self):
        return 54

    def set_brightness(self, brightness_value):
        return

    def get_gain(self):
        return 32

    def set_gain(self, gain_value):
        return

    def get_gamma(self):
        return 22

    def set_gamma(self, gamma_value):
        return

    def get_exposure_time(self):
        return 0.23

    def get_video_live(self):
        return True

    def get_raw_image_size(self):
        return list(self.image_dimensions)

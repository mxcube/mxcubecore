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
#   You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import gevent
import numpy as np

from PyQt4 import QtGui
from PyQt4 import QtCore

from HardwareRepository.BaseHardwareObjects import Device


class Qt4_VideoMockup(Device):
    """
    Descript. :
    """
    def __init__(self, name):
        """
        Descript. :
        """
        Device.__init__(self, name)
        self.force_update = None
        self.image_dimensions = None
        self.image_polling = None
        self.image_type = None
        self.image = None
        self.sleep_time = 1

    def init(self):
        """
        Descript. :
        """ 
        current_path = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
        current_path = os.path.join(*current_path[1:-1])
        image_path = os.path.join("/", current_path, "ExampleFiles/fakeimg.jpg")
        self.image = QtGui.QPixmap(image_path)
        self.image_dimensions = (self.image.width(), self.image.height())
        self.setIsReady(True)
        self.sleep_time = self.getProperty("interval")

    def start_camera(self):
        if self.image_polling is None:
            self.image_polling = gevent.spawn(self._do_imagePolling, 1.0 / self.sleep_time)

    def get_image_dimensions(self):
        return self.image_dimensions

    def imageType(self):
        """
        Descript. :
        """
        return

    def setLive(self, mode):
        """
        Descript. :
        """
        return
    
    def getWidth(self):
        """
        Descript. :
        """
        return self.image_dimensions[0]
	
    def getHeight(self):
        """
        Descript. :
        """
        return self.image_dimensions[1]

    def _do_imagePolling(self, sleep_time):
        """
        Descript. :
        """ 
        while True:
            self.emit("imageReceived", self.image)
            gevent.sleep(sleep_time)

    def save_snapshot(self, filename, image_type='PNG'):
        qimage = QtGui.QImage(self.image)
        qimage.save(filename, image_type)

    def get_snapshot(self, bw=None, return_as_array=None):
        qimage = QtGui.QImage(self.image)
        if return_as_array:
            qimage = qimage.convertToFormat(4)
            ptr = qimage.bits()
            ptr.setsize(qimage.byteCount())

            image_array = np.array(ptr).reshape(qimage.height(), qimage.width(), 4)
            if bw:
                return np.dot(image_array[...,:3], [0.299, 0.587, 0.144])
            else:
                return image_array
        else:
            if bw:
                return qimage.convertToFormat(QtGui.QImage.Format_Mono)
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

    def set_exposure_time(self, exposure_time_value):
        return

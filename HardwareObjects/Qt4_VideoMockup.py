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
import time
import gevent

from PyQt4.QtGui import QImage

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

    def init(self):
        """
        Descript. :
        """ 
        self.image = QImage()

        current_path = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
        current_path = os.path.join(*current_path[1:-1])
        image_path = os.path.join("/", current_path, "ExampleFiles/fakeimg.jpg")
        self.image.load(image_path)
        self.image_dimensions = (self.image.width(), self.image.height())
        self.setIsReady(True)
 
    def start_camera(self):
        if self.image_polling is None:
            self.image_polling = gevent.spawn(self._do_imagePolling, 1)

    def get_image_dimensions(self):
        return self.image_dimensions

    def imageType(self):
        """
        Descript. :
        """
        return

    def contrastExists(self):
        """
        Descript. :
        """
        return

    def setContrast(self, contrast):
        """
        Descript. :
        """
        return

    def getContrast(self):
        """
        Descript. :
        """
        return 

    def getContrastMinMax(self):
        """
        Descript. :
        """
        return 

    def brightnessExists(self):
        """
        Descript. :
        """
        return

    def setBrightness(self, brightness):
        """
        Descript. :
        """
        return

    def getBrightness(self):
        """
        Descript. :
        """ 
        return 

    def getBrightnessMinMax(self):
        """
        Descript. :
        """
        return 

    def gainExists(self):
        """
        Descript. :
        """
        return

    def setGain(self, gain):
        """
        Descript. :
        """
        return

    def getGain(self):
        """
        Descript. :
        """
        return

    def getGainMinMax(self):
        """
        Descript. :
        """
        return 

    def gammaExists(self):
        """
        Descript. :
        """
        return

    def setGamma(self, gamma):
        """
        Descript. :
        """
        return

    def getGamma(self):
        """
        Descript. :
        """
        return 

    def getGammaMinMax(self):
        """
        Descript. :
        """ 
        return (0, 1)

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

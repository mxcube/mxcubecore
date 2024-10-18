"""
Descript. :
"""

import os
import time

import gevent
from gui.utils.qt_import import QImage

from mxcubecore import BaseHardwareObjects
from mxcubecore.HardwareObjects.Camera import JpegType


class VideoMockup(BaseHardwareObjects.Device):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        BaseHardwareObjects.Device.__init__(self, name)
        self.force_update = None
        self.image_dimensions = None
        self.image_polling = None
        self.image_type = None
        self.qimage = None

    def init(self):
        """
        Descript. :
        """
        self.qimage = QImage()
        current_path = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
        current_path = os.path.join(*current_path[1:-1])
        image_path = os.path.join("/", current_path, "ExampleFiles/fakeimg.jpg")
        self.qimage.load(image_path)
        self.force_update = False
        self.image_dimensions = [600, 400]
        self.image_type = JpegType()
        self.set_is_ready(True)

    def imageType(self):
        """
        Descript. :
        """
        return self.image_type

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

    def set_live(self, mode):
        """
        Descript. :
        """
        return

    def get_width(self):
        """
        Descript. :
        """
        return self.image_dimensions[0]

    def get_height(self):
        """
        Descript. :
        """
        return self.image_dimensions[1]

    def _do_imagePolling(self, sleep_time):
        """
        Descript. :
        """
        self.image_dimensions = (self.qimage.width(), self.qimage.height())
        while True:
            self.emit(
                "imageReceived",
                self.qimage,
                self.qimage.width(),
                self.qimage.height(),
                self.force_update,
            )
            time.sleep(sleep_time)

    def connect_notify(self, signal):
        """
        Descript. :
        """
        if signal == "imageReceived":
            self.image_polling = gevent.spawn(self._do_imagePolling, 1)

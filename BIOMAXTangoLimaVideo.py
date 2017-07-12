"""Class for cameras connected to Lima Tango Device Servers
"""
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import CommandContainer
from HardwareRepository import HardwareRepository
from HardwareRepository.HardwareObjects.Camera import JpegType, BayerType, MmapType, RawType, RGBType
#from Qub.CTools import pixmaptools
from PyQt4.QtGui import QImage
import gevent
import logging
import os
import time
import sys
import PyTango
from PyTango.gevent import DeviceProxy
import numpy
import struct

class BIOMAXTangoLimaVideo(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.__brightnessExists = False
        self.__contrastExists = False
        self.__gainExists = False
        self.__gammaExists = False
        self.__polling = None
        #self.scaling = pixmaptools.LUT.Scaling()

    def init(self):
        self.device = None

        try:
            self.device = DeviceProxy(self.tangoname)
            #try a first call to get an exception if the device
            #is not exported
            self.device.ping()
            logging.getLogger('HWR').error("%s: %s", str(self.name()), "WTF Connected")
            self.image_dimensions = [self.device.image_height, self.device.image_width]
            #self.image_dimensions = [self.device.image_width, self.device.image_height]
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error.desc)

            self.device = BaseHardwareObjects.Null()
        else:
            self.setExposure(self.getProperty("interval")/1000.0)
            self.device.video_mode = "RGB24"

        self.video_exposure = self.getProperty("interval")/1000.0

        self.chan_zoom = self.addChannel({"type":"exporter", "name":"ImageZoom"  }, 'ImageZoom')
        try:
            self.zoom = float(self.getProperty("image_zoom"))
            self.chan_zoom.setValue(self.zoom)
        except:
            logging.getLogger("HWR").info( "cannot set image zoom level")

        self.setIsReady(True)


    def imageType(self):
        return BayerType("RGB24")

    def _get_last_image(self):
        img_data = self.device.video_last_image
        if img_data[0]=="VIDEO_IMAGE":
            header_fmt = "<IHHqiiHHHH"
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(header_fmt, img_data[1][:struct.calcsize(header_fmt)])
            raw_buffer = img_data[1][struct.calcsize(header_fmt):]

            qimage = QImage(raw_buffer, width, height, width*3, QImage.Format_RGB888)
            return qimage

    def _do_polling(self, sleep_time):
        while True:
            qimage = self._get_last_image()
            qimage.save("/tmp/md3_jn.jpeg")
            # temp solution
            import base64
            with open("/tmp/md3_jn.jpeg", "rb") as imageFile:
                imgStr = imageFile.read()
            self.emit("imageReceived", imgStr, qimage.width(), qimage.height())
            time.sleep(sleep_time)

    def connectNotify(self, signal):
        if signal=="imageReceived":
            if self.__polling is None:
                self.__polling = gevent.spawn(self._do_polling, self.video_exposure)#self.device.video_exposure)


    #############   CONTRAST   #################
    def contrastExists(self):
        return self.__contrastExists

    #############   BRIGHTNESS   #################
    def brightnessExists(self):
        return self.__brightnessExists

    #############   GAIN   #################
    def gainExists(self):
        return self.__gainExists

    #############   GAMMA   #################
    def gammaExists(self):
        return self.__gammaExists

    #############   WIDTH   #################
    def getWidth(self):
        """tango"""
        # it's wrong in the tango device
        return self.device.image_height

    def getHeight(self):
        """tango"""
        # same as above
        return self.device.image_width
    
    def setSize(self, width, height):
        """Set new image size

        Only takes width into account, because anyway
        we can only set a scale factor
        """
        return

    def takeSnapshot(self, *args, **kwargs):
        """tango"""
        qimage = self._get_last_image()
        try:
            qimage.save(args[0], "PNG")
        except:
            logging.getLogger("HWR").exception("%s: could not save snapshot", self.name())
            return False
        else:
            return True

    def setLive(self, mode):
        """tango"""
        if mode:
            self.device.video_live=True
        else:
            self.device.video_live=False

    def setExposure(self, exposure):
        self.device.video_exposure = exposure

    def get_image_zoom(self):
        return self.chan_zoom.getValue()


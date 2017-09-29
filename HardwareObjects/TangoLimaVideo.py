"""Class for cameras connected to Lima Tango Device Servers
"""
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import CommandContainer
from HardwareRepository import HardwareRepository
from HardwareRepository.HardwareObjects.Camera import JpegType, BayerType, MmapType, RawType, RGBType
from Qub.CTools import pixmaptools
import gevent
import logging
import os
import time
import sys
import PyTango
from PyTango.gevent import DeviceProxy
import numpy
import struct

class TangoLimaVideo(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.__brightnessExists = False
        self.__contrastExists = False
        self.__gainExists = False
        self.__gammaExists = False
        self.__polling = None
        self.scaling = pixmaptools.LUT.Scaling()
        
    def init(self):
        self.device = None
        
        try:
            self.device = DeviceProxy(self.tangoname)
            #try a first call to get an exception if the device
            #is not exported
            self.device.ping()
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error.desc)
            
            self.device = BaseHardwareObjects.Null()
        else:
            self.setExposure(self.getProperty("interval")/1000.0)
            self.device.video_mode = "BAYER_RG16"

        self.setIsReady(True)

    def imageType(self):
        return BayerType("RG16")

    def _get_last_image(self):
        img_data = self.device.video_last_image
        if img_data[0]=="VIDEO_IMAGE":
            header_fmt = ">IHHqiiHHHH"
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(header_fmt, img_data[1][:struct.calcsize(header_fmt)])
            raw_buffer = numpy.fromstring(img_data[1][32:], numpy.uint16)
            self.scaling.autoscale_min_max(raw_buffer, width, height, pixmaptools.LUT.Scaling.BAYER_RG16)
            validFlag, qimage = pixmaptools.LUT.raw_video_2_image(raw_buffer,
                                                                  width, height,
                                                                  pixmaptools.LUT.Scaling.BAYER_RG16,
                                                                  self.scaling)
            if validFlag:
                return qimage

    def _do_polling(self, sleep_time):
        while True:
            qimage = self._get_last_image()
            self.emit("imageReceived", qimage, qimage.width(), qimage.height(), False)

            time.sleep(sleep_time)

    def connectNotify(self, signal):
        if signal=="imageReceived":
            if self.__polling is None:
                self.__polling = gevent.spawn(self._do_polling, self.device.video_exposure)


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
        return self.device.image_width

    def getHeight(self):
        """tango"""
        return self.device.image_height
    
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


"""Class for cameras connected to Lima Tango Device Servers

Example configuration:
----------------------
<device class="TangoLimaVideo">
  <username>Prosilica 1350C</username>
  <tangoname>id23/limaccd/minidiff2</tangoname>
  <bpmname>id23/limabeamviewer/minidiff2</bpmname>
  <interval>15</interval>
  <video_mode>RGB24</video_mode>
</device>

If video mode is not specified, BAYER_RG16 is used by default.
"""
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import CommandContainer
from HardwareRepository import HardwareRepository
from HardwareRepository.HardwareObjects.Camera import (
    JpegType,
    BayerType,
    MmapType,
    RawType,
    RGBType,
)
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
        self._video_mode = "BAYER_RG16"
        self.scaling = pixmaptools.LUT.Scaling()
        self.scaling.set_custom_mapping(0, 255)

    def init(self):
        self.device = None

        try:
            self.device = DeviceProxy(self.tangoname)
            # try a first call to get an exception if the device
            # is not exported
            self.device.ping()
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error("%s: %s", str(self.name()), last_error.desc)

            self.device = BaseHardwareObjects.Null()
        else:
            self._video_mode = self.getProperty("video_mode") or "BAYER_RG16"
            self.device.video_mode = self._video_mode
            if self.getProperty("exposure_time"):
                self.setExposure(float(self.getProperty("exposure_time")))
            else:
                self.setExposure(self.getProperty("interval") / 1000.0)

        self.setIsReady(True)

    def imageType(self):
        return BayerType("RG16") if self._video_mode == "BAYER_RG16" else RGBType(None)

    def _get_last_image(self):
        img_data = self.device.video_last_image
        if img_data[0] == "VIDEO_IMAGE":
            header_fmt = ">IHHqiiHHHH"
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
                header_fmt, img_data[1][: struct.calcsize(header_fmt)]
            )
            if self._video_mode == "BAYER_RG16":
                raw_buffer = numpy.fromstring(img_data[1][32:], numpy.uint16)
                self.scaling.autoscale_min_max(
                    raw_buffer, width, height, pixmaptools.LUT.Scaling.BAYER_RG16
                )
            else:
                raw_buffer = numpy.fromstring(img_data[1][32:], numpy.uint8)
            validFlag, qimage = pixmaptools.LUT.raw_video_2_image(
                raw_buffer,
                width,
                height,
                pixmaptools.LUT.Scaling.RGB24
                if self._video_mode == "RGB24"
                else pixmaptools.LUT.Scaling.BAYER_RG16,
                self.scaling,
            )
            if validFlag:
                return qimage

    def _do_polling(self, sleep_time):
        while True:
            qimage = self._get_last_image()
            self.emit("imageReceived", qimage, qimage.width(), qimage.height(), False)

            time.sleep(sleep_time)

    def connectNotify(self, signal):
        if signal == "imageReceived":
            if self.__polling is None:
                self.__polling = gevent.spawn(
                    self._do_polling, self.device.video_exposure
                )

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
        except BaseException:
            logging.getLogger("HWR").exception(
                "%s: could not save snapshot", self.name()
            )
            return False
        else:
            return True

    def setLive(self, mode):
        """tango"""
        curr_state = self.device.video_live
        if mode:
            if not curr_state:
                self.device.video_live = True
        else:
            if curr_state:
                self.device.video_live = False

    def setExposure(self, exposure):
        self.device.video_exposure = exposure

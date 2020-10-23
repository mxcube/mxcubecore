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
import logging
import time
import struct
import numpy
import gevent
import PyTango
from PIL import Image
import io
import gipc
import os

from PyTango.gevent import DeviceProxy

from HardwareRepository import BaseHardwareObjects


def poll_image(lima_tango_device, video_mode, FORMATS):
    img_data = lima_tango_device.video_last_image

    hfmt = ">IHHqiiHHHH"
    hsize = struct.calcsize(hfmt)
    _, _, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
        hfmt, img_data[1][:hsize]
    )

    raw_data = img_data[1][hsize:]
    _from, _to = FORMATS.get(video_mode, (None, None))

    if _from and _to:
        img = Image.frombuffer(_from, (height, width), raw_data, "raw", _from, 0, 1)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format=_to)
        img = img.tobytes()
    else:
        img = raw_data

    return img, width, height


class TangoLimaVideo(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.__brightnessExists = False
        self.__contrastExists = False
        self.__gainExists = False
        self.__gammaExists = False
        self.__polling = None
        self._video_mode = None
        self._last_image = (0, 0, 0)

        # Dictionary containing conversion information for a given
        # video_mode. The camera video mode is the key and the first
        # index of the tuple contains the corresponding PIL mapping
        # and the second the desried output format. The image is
        # passed on as it is of the video mode is not in the dictionary
        self._FORMATS = {
            "RGB8": ("L", "BMP"),
            "RGB24": ("RGB", "BMP"),
            "RGB32": ("RGBA", "BMP"),
            "NO_CONVERSION": (None, None),
        }

    def init(self):
        self.device = None

        try:
            self._video_mode = self.get_property("video_mode", "RGB24")
            self.device = DeviceProxy(self.tangoname)
            # try a first call to get an exception if the device
            # is not exported
            self.device.ping()
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error("%s: %s", str(self.name()), last_error.desc)

            self.device = BaseHardwareObjects.Null()
        else:
            if self.get_property("exposure_time"):
                self._sleep_time = float(self.get_property("exposure_time"))
            elif self.get_property("interval"):
                self._sleep_time = float(self.get_property("interval")) / 1000.0

            if self.get_property("control_video", "True"):
                logging.getLogger("HWR").info("MXCuBE controlling video")

                if self.device.video_live:
                    self.device.video_live = False

                self.device.video_mode = self._video_mode
                self.set_exposure(self._sleep_time)

                self.device.video_live = True
            else:
                logging.getLogger("HWR").info("MXCuBE NOT controlling video")

        self.set_is_ready(True)

    def get_last_image(self):
        return self._last_image

    def _do_polling(self, sleep_time):
        lima_tango_device = self.device

        while True:
            data, width, height = poll_image(
                lima_tango_device, self.video_mode, self._FORMATS
            )

            self._last_image = data, width, heigh
            self.emit("imageReceived", data, width, height, False)
            time.sleep(sleep_time)

    def connect_notify(self, signal):
        if signal == "imageReceived":
            if self.__polling is None:
                self.__polling = gevent.spawn(
                    self._do_polling, self.device.video_exposure
                )

    def get_width(self):
        return self.device.image_width

    def get_height(self):
        return self.device.image_height

    def take_snapshot(self, path=None, bw=False):
        data, width, height = poll_image(self.device, self.video_mode, self._FORMATS)

        img = Image.frombytes("RGB", (width, height), data)

        if bw:
            img.convert("1")

        if path:
            img.save(path)

        return img

    def set_live(self, mode):
        curr_state = self.device.video_live

        if mode:
            if not curr_state:
                self.device.video_live = True
        else:
            if curr_state:
                self.device.video_live = False

    def set_exposure(self, exposure):
        self.device.video_exposure = exposure

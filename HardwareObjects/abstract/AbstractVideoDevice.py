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
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
GenericVideo

[Description]
This module declares class GenericVideo.

This class is not meant to be instanced directly but as
the base class for classes providing access to Video in MXCuBE


"""

from __future__ import print_function
import abc
import os
import sys
import time
import logging
import gevent
import numpy as np

try:
    import cv2
except Exception:
    pass

from HardwareRepository.BaseHardwareObjects import Device


modulenames = ["qt", "PyQt5", "PyQt4"]

if any(mod in sys.modules for mod in modulenames):
    USEQT = True
    try:
        from PyQt5.QtGui import QImage, QPixmap
    except ImportError:
        from PyQt4.QtGui import QImage, QPixmap
else:
    USEQT = False
    from PIL import Image


class AbstractVideoDevice(Device):

    default_cam_encoding = "yuv422p"
    default_poll_interval = 50
    default_cam_type = "basler"
    default_scale_factor = 1.0

    def __init__(self, name):
        Device.__init__(self, name)

        self.cam_mirror = None
        self.cam_encoding = None
        self.cam_gain = None
        self.cam_exposure = None
        self.poll_interval = None
        self.cam_type = None
        self.cam_scale_factor = None
        self.cam_name = None

        self.raw_image_dimensions = [None, None]
        self.image_dimensions = [None, None]
        self.image_polling = None
        self.image_format = None  # not used
        self.default_cam_encoding = None
        self.default_poll_interval = None

        self.decoder = None

    def init(self):
        self.cam_name = self.getProperty("name", "camera")

        try:
            self.cam_mirror = eval(self.getProperty("mirror"))
        except Exception:
            self.cam_mirror = [False, False]

        try:
            self.cam_encoding = self.getProperty("encoding").lower()
        except Exception:
            pass

        scale = self.getProperty("scale")
        if scale is None:
            self.cam_scale_factor = self.default_scale_factor
        else:
            try:
                self.cam_scale_factor = eval(scale)
            except Exception:
                logging.getLogger().warning(
                    "%s: failed to interpret scale factor for camera." "Using default.",
                    self.name(),
                )
                self.cam_scale_factor = self.default_scale_factor

        try:
            self.poll_interval = self.getProperty("interval")
        except Exception:
            self.poll_interval = 1

        try:
            self.cam_gain = float(self.getProperty("gain"))
        except Exception:
            pass

        try:
            self.cam_exposure = float(self.getProperty("exposure"))
        except Exception:
            pass

        self.scale = self.getProperty("scale", 1.0)

        try:
            self.cam_type = self.getProperty("type").lower()
        except Exception:
            pass

        # Apply defaults if necessary
        if self.cam_encoding is None:
            self.cam_encoding = AbstractVideoDevice.default_cam_encoding

        if self.poll_interval is None:
            self.poll_interval = self.default_poll_interval

        if self.cam_exposure is None:
            self.cam_exposure = self.poll_interval / 1000.0

        if self.cam_type is None:
            self.cam_type = self.default_cam_type

        # Apply values

        self.set_video_live(False)
        time.sleep(0.1)
        self.set_cam_encoding(self.cam_encoding)
        self.set_exposure_time(self.cam_exposure)

        if self.cam_gain is not None:
            self.set_gain(self.cam_gain)

        self.image_dimensions = self.get_image_dimensions()

        # Start polling greenlet
        if self.image_polling is None:
            self.set_video_live(True)
            self.change_owner()

            logging.getLogger("HWR").info("Starting polling for camera")
            self.image_polling = gevent.spawn(
                self.do_image_polling, self.poll_interval / 1000.0
            )
            self.image_polling.link_exception(self.polling_ended_exc)
            self.image_polling.link(self.polling_ended)

        self.setIsReady(True)

    def get_camera_name(self):
        return self.cam_name

    def polling_ended(self, gl=None):
        logging.getLogger("HWR").info("Polling ended for qt4 camera")

    def polling_ended_exc(self, gl=None):
        logging.getLogger("HWR").info("Polling ended exception for qt4 camera")

    """ Generic methods """

    def get_new_image(self):
        """
        Descript. :
        """
        raw_buffer, width, height = self.get_image()

        if raw_buffer is not None and raw_buffer.any():
            if self.decoder:
                raw_buffer = self.decoder(raw_buffer)
                qimage = QImage(
                    raw_buffer, width, height, width * 3, QImage.Format_RGB888
                )
            
            else:
                qimage = QImage(raw_buffer, width, height, QImage.Format_RGB888)

            if self.cam_mirror is not None:
                qimage = qimage.mirrored(self.cam_mirror[0], self.cam_mirror[1])

            if self.scale != 1:
                dims = self.get_image_dimensions()  # should be already scaled
                qimage = qimage.scaled(QSize(dims[0], dims[1]))

            qpixmap = QPixmap(qimage)
            self.emit("imageReceived", qpixmap)
            return qimage.copy()

    def get_jpg_image(self):
        """ for now this function allows to deal with prosilica or any RGB encoded video data"""
        """
           the signal imageReceived is as expected by mxcube3
        """
        raw_buffer, width, height = self.get_image()

        if raw_buffer is not None and raw_buffer.any():
            image = Image.frombytes("RGB", (width, height), raw_buffer)
            from cStringIO import StringIO

            strbuf = StringIO()
            image.save(strbuf, "JPEG")
            jpgimg_str = strbuf.getvalue()
            if jpgimg_str is not None:
                self.emit("imageReceived", jpgimg_str, width, height)
            return jpgimg_str
        else:
            return None

    def get_cam_type(self):
        return self.cam_type

    def y8_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        raw_dims = self.get_raw_image_size()
        image.resize(raw_dims[1], raw_dims[0], 1)
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    def y16_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        raw_dims = self.get_raw_image_size()
        np.resize(image, (raw_dims[1], raw_dims[0], 2))
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    def yuv_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        raw_dims = self.get_raw_image_size()
        image.resize(raw_dims[1], raw_dims[0], 2)
        return cv2.cvtColor(image, cv2.COLOR_YUV2RGB_UYVY)

    def bayer_rg16_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint16)
        raw_dims = self.get_raw_image_size()
        image.resize(raw_dims[1], raw_dims[0])
        out_buffer =  cv2.cvtColor(image, cv2.COLOR_BayerRG2BGR)
        if out_buffer.ndim == 3 and out_buffer.itemsize > 1:
            # decoding bayer16 gives 12 bit values => scale to 8 bit
            out_buffer = np.right_shift(out_buffer, 4).astype(np.uint8)
        return out_buffer

    def save_snapshot(self, filename, image_type="PNG"):
        if USEQT:
            qimage = self.get_new_image()
            qimage.save(filename, image_type)
        else:
            jpgstr = self.get_jpg_image()
            open(filename, "w").write(jpgstr)

    def get_snapshot(self, bw=None, return_as_array=True):
        if not USEQT:
            print("get snapshot not implemented yet for non-qt mode")
            return None

        qimage = self.get_new_image()
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

    def get_scaling_factor(self):
        """
        Descript. :
        Returns   : Scaling factor in float. None if does not exists
        """
        return self.cam_scale_factor

    get_image_zoom = get_scaling_factor

    def imageType(self):
        """
        Descript. : returns image type (not used)
        """
        return self.image_format

    def start_camera(self):
        return

    def setLive(self, mode):
        """
        Descript. :
        """
        return
        if mode:
            self.set_video_live(True)
            self.change_owner()
        else:
            self.set_video_live(False)

    def change_owner(self):
        """LIMA specific, because it has to be root at startup
           move this to Qt4_LimaVideo
        """
        if os.getuid() == 0:
            try:
                os.setgid(int(os.getenv("SUDO_GID")))
                os.setuid(int(os.getenv("SUDO_UID")))
            except Exception:
                logging.getLogger().warning(
                    "%s: failed to change the process" "ownership.", self.name()
                )

    def getWidth(self):
        """
        Descript. :
        """
        return int(self.image_dimensions[0])

    def getHeight(self):
        """
        Descript. :
        """
        return int(self.image_dimensions[1])

    def do_image_polling(self, sleep_time):
        """
        Descript. :
        """
        while self.get_video_live() is True:
            if USEQT:
                self.get_new_image()
            else:
                self.get_jpg_image()
            time.sleep(sleep_time)

    def connectNotify(self, signal):
        """
        Descript. :
        """
        return

        """if signal == "imageReceived" and self.image_polling is None:
            self.image_polling = gevent.spawn(self.do_image_polling,
                 self.poll_interval/1000.0)"""

    def refresh_video(self):
        """
        Descript. :
        """
        pass

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            self.decoder = self.yuv_2_rgb
        elif cam_encoding == "y8":
            self.decoder = self.y8_2_rgb
        elif cam_encoding == "y16":
            self.decoder = self.y16_2_rgb
        elif cam_encoding.lower() == "bayer_rg16":
            self.decoder = self.bayer_rg16_2_rgb
        self.cam_encoding = cam_encoding
        
    def get_image_dimensions(self):
        raw_width, raw_height = self.get_raw_image_size()
        width = raw_width * self.scale
        height = raw_height * self.scale
        return [width, height]

    """  Methods to be implemented by the implementing class """

    def get_raw_image_size(self):
        # Must return a two-value list necessary to avoid breaking e.g. ViideoMockup
        return [None, None]

    @abc.abstractmethod
    def get_image(self):
        """ The implementing class should return here the latest_image in
        raw_format, followed by the width and height of the image"""
        pass

    @abc.abstractmethod
    def get_gain(self):
        pass

    @abc.abstractmethod
    def set_gain(self, gain_value):
        pass

    @abc.abstractmethod
    def get_exposure_time(self):
        pass

    @abc.abstractmethod
    def set_exposure_time(self, exposure_time_value):
        pass

    @abc.abstractmethod
    def get_video_live(self):
        pass

    @abc.abstractmethod
    def set_video_live(self, flag):
        pass

    # Other (no implementation for now. Can be overloaded, otherwise dummy)
    def get_gamma(self):
        return

    def set_gamma(self, gamma_value):
        return

    def get_contrast(self):
        return

    def set_contrast(self, contrast_value):
        return

    def get_brightness(self):
        return

    def set_brightness(self, brightness_value):
        return


def test_hwo(hwo):
    print("Image dimensions: ", hwo.get_image_dimensions())
    print("Live Mode: ", hwo.get_video_live())

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

import abc

import os
import time
import logging
import gevent
import numpy as np

from QtImport import *

try:
    import cv2
except:
    pass

from HardwareRepository.BaseHardwareObjects import Device

class GenericVideoDevice(Device):

    default_cam_encoding = "yuv422p"
    default_poll_interval = 50
    default_cam_type = "basler"

    def __init__(self, name):
        Device.__init__(self,name)

        self.cam_mirror = None
        self.cam_encoding = None
        self.cam_gain = None
        self.cam_exposure = None
        self.poll_interval = None
        self.cam_type = None

        self.cam_scale_factor = None

        self.image_dimensions = [None,None]
        self.image_polling = None
        self.image_format = None # not used
        self.default_cam_encoding = None
        self.default_poll_interval = None

    def init(self):
        

        # Read values from XML
        try:
            self.cam_mirror = eval(self.getProperty("mirror"))
        except:
            self.cam_mirror = [False, False]

        try:
            self.cam_encoding = self.getProperty("encoding").lower()
        except:
            pass

        try:
            self.poll_interval = self.getProperty("interval")
        except:
            self.poll_interval = 1

        try:
            self.cam_gain = float(self.getProperty("gain"))
        except:
            pass

        try:
            self.cam_exposure = float(self.getProperty("exposure"))
        except:
            pass

        try:
            self.cam_type = self.getProperty("type").lower()
        except:
            pass

        # Apply defaults if necessary
        if self.cam_encoding is None:
            self.cam_encoding = self.default_cam_encoding

        if self.poll_interval is None:
            self.poll_interval = self.default_poll_interval

        if self.cam_exposure is None:
            self.cam_exposure = self.poll_interval/1000.0

        if self.cam_type is None:
            self.cam_exposure = self.default_cam_type

        # Apply values	

        self.set_cam_encoding(self.cam_encoding)
        self.set_exposure_time(self.cam_exposure)

        if self.cam_gain is not None:
            self.set_gain(self.cam_gain)

        self.image_dimensions = self.get_image_dimensions()

        # Start polling greenlet
        if self.image_polling is None:
            self.set_video_live(True)
            self.change_owner()

            self.image_polling = gevent.spawn(self.do_image_polling,
                                              self.poll_interval/1000.0)

        self.setIsReady(True)

    """ Generic methods """
    def get_new_image(self):
        """
        Descript. :
        """
        raw_buffer, width, height = self.get_image()

        if raw_buffer:
            if self.cam_type == "basler":
                raw_buffer = self.decoder(raw_buffer)
                qimage = QImage(raw_buffer, width, height,
                                width * 3,
                                QImage.Format_RGB888)
            else:
                qimage = QImage(raw_buffer, width, height,
                                QImage.Format_RGB888)

            if self.cam_mirror is not None:
                qimage = qimage.mirrored(self.cam_mirror[0], self.cam_mirror[1])     

            qpixmap = QPixmap(qimage)
            self.emit("imageReceived", qpixmap)
            return qimage

    def get_cam_type(self):
        return self.cam_type

    def y8_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        image.resize(self.image_dimensions[1], self.image_dimensions[0], 1)
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    def yuv_2_rgb(self, raw_buffer):
        image = np.fromstring(raw_buffer, dtype=np.uint8)
        image.resize(self.image_dimensions[1], self.image_dimensions[0], 2)
        return cv2.cvtColor(image, cv2.COLOR_YUV2RGB_UYVY)

    def save_snapshot(self, filename, image_type='PNG'):
        qimage = self.get_new_image() 
        qimage.save(filename, image_type) 

    def get_snapshot(self, bw=None, return_as_array=True):
        qimage = self.get_new_image()
        if return_as_array:
            qimage = qimage.convertToFormat(4)
            ptr = qimage.bits()
            ptr.setsize(qimage.byteCount())
            image_array = np.array(ptr).reshape(qimage.height(),
                                                qimage.width(), 4)
            if bw:
                return np.dot(image_array[...,:3],[0.299, 0.587, 0.144])
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
        """
        Descript. :
        """
        if os.getuid() == 0:
            try:
                os.setgid(int(os.getenv("SUDO_GID")))
                os.setuid(int(os.getenv("SUDO_UID")))
            except:
                logging.getLogger().warning('%s: failed to change the process'
                                            'ownership.', self.name())
 
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
        while self.get_video_live() == True:
            self.get_new_image()
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

    """  Methods to be implemented by the implementing class """
    @abc.abstractmethod
    def get_image_dimensions(self):
        pass

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
    print "Image dimensions: ", hwo.get_image_dimensions()
    print "Live Mode: ", hwo.get_video_live()

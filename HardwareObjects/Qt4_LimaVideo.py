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
Qt4_LimaVideo

[Description]
HwObj used to grab images via LImA library or Lima Tango server.

[Configuration]
See example below.  To select between "Library" or "Tango" simply
use and configure the field <address> (for Library) 
or <tangoname> (for Tango)
in the XML file.


Example Hardware Object XML file :
==================================
<device class="Qt4_LimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <address>84.89.227.6</address>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</device>
"""

import os
import time
import logging
import gevent
import struct
import numpy as np

from PyQt4 import QtGui

try:
    from Lima import Core
except:
    pass

try:
    import PyTango
except ImportError, e:
    pass

try:
    from Lima import Prosilica
except ImportError, e:
    pass

try:
    from Lima import Basler
except ImportError, e:
    pass

try:
    import cv2
except ImportError:
    pass 

from HardwareRepository.BaseHardwareObjects import Device

class Qt4_LimaVideo(Device):
    """
    Descript. : 
    """
    def __init__(self, name):
        """
        Descript. :
        """
        Device.__init__(self, name)

        self.force_update = None

        self.access_type = "LIMA"

        self.cam_type = "basler" # default
        self.cam_address = None
        self.cam_mirror = None
        self.cam_scale_factor = None
        self.cam_encoding = None        

        self.brightness_exists = None 
        self.contrast_exists = None
        self.gain_exists = None
        self.gamma_exists = None

        self.qimage = None
        self.image_format = None
        self.image_dimensions = None

        # LIMA access
        self.camera = None
        self.interface = None
        self.control = None
        self.video = None 

        # TANGO access
        self.device = None

        self.image_polling = None
        self.decoder = None

    def init(self):
        """
        Descript. : 
        """

        tangoname = self.getProperty("tangoname")
        self.cam_address = self.getProperty("address")
        self.cam_type = self.getProperty("type").lower()

        if tangoname is not None:
            self.init_tango(tangoname)
        elif self.cam_address is not None:
            self.init_lima()

        self.set_exposure_time(self.getProperty("interval")/1000.0)
        self.set_cam_encoding("yuv422g")  # default value

        self.setIsReady(True)

        self.force_update = False

        try:       
            self.cam_mirror = eval(self.getProperty("mirror"))
        except:
            pass        


        # Basler
        try:
            self.cam_encoding = self.getProperty("encoding").lower()
        except:
            logging.getLogger().error("Cannot get encoding from xml file!")
            raise

        self.set_cam_encoding(self.cam_encoding)

        try:
            self.cam_gain = float(self.getProperty("gain"))
            self.set_gain(self.cam_gain)
            logging.getLogger().info("%s: Setting camera gain to %s",
                                     self.name(), self.cam_gain)
        except:
            pass

        try:
            self.cam_exposure = float(self.getProperty("exposure"))
            self.set_exposure_time(self.cam_exposure)
            logging.getLogger().info("%s: Setting exposure to %s s",
                                     self.name(), self.cam_exposure)
        except:
            pass

        self.setIsReady(True)

        if self.image_polling is None:
            self.set_video_live(True)
            self.change_owner()

            self.image_polling = gevent.spawn(self.do_image_polling,
                                              self.getProperty("interval") /
                                              1000.0)

    def init_tango(self, tangoname):
        self.access_type = "TANGO"

        try:
            self.device = PyTango.DeviceProxy(tangoname)
            self.device.ping()
            self.image_dimensions = [self.device.image_width, self.device.image_height]
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error.desc)

            self.device = BaseHardwareObjects.Null()


    def init_lima(self):
        self.access_type = "LIMA"

        if self.cam_type == 'prosilica':
            self.camera = Prosilica.Camera(self.cam_address)
            self.interface = Prosilica.Interface(self.camera) 
        elif self.cam_type == 'basler':
            logging.getLogger("HWR").info("Connecting to camera with address %s" % self.cam_address)
            self.camera = Basler.Camera(self.cam_address)
            self.interface = Basler.Interface(self.camera)
 
        self.control = Core.CtControl(self.interface)
        self.video = self.control.video()

        if self.cam_type == 'prosilica':
            self.image_dimensions = list(self.camera.getMaxWidthHeight())
        elif self.cam_type == 'basler':
            width = self.camera.getRoi().getSize().getWidth()
            height = self.camera.getRoi().getSize().getHeight()
            self.image_dimensions = [width, height]

    def is_tango(self):
        return self.access_type == "TANGO"

    def is_lima(self):
        return self.access_type == "LIMA"

    def get_image_dimensions(self):
        return self.image_dimensions

    def get_scaling_factor(self):
        """
        Descript. :
        Returns   : Scaling factor in float. None if does not exists
        """ 
        return self.cam_scale_factor

    def imageType(self):
        """
        Descript. : returns image type
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
                 self.getProperty("interval")/1000.0)"""

    def refresh_video(self):
        """
        Descript. :
        """
        pass
 
    def get_new_image(self):
        """
        Descript. :
        """
        if self.is_tango():
            raw_buffer, width, height = self.get_tango_image()
        else:
            raw_buffer, width, height = self.get_lima_image()

        if self.cam_type == "basler":
            raw_buffer = self.decoder(raw_buffer)
            qimage = QtGui.QImage(raw_buffer, width, height,
                                  width * 3,
                                  QtGui.QImage.Format_RGB888)
        else:
            qimage = QtGui.QImage(raw_buffer, width, height,
                                  QtGui.QImage.Format_RGB888)

        if self.cam_mirror is not None:
            qimage = qimage.mirrored(self.cam_mirror[0], self.cam_mirror[1])     

        qpixmap = QtGui.QPixmap(qimage)
        self.emit("imageReceived", qpixmap)
        return qimage

    def get_tango_image(self):
        img_data = self.device.video_last_image

        if img_data[0]=="VIDEO_IMAGE":
            header_fmt = ">IHHqiiHHHH"
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(header_fmt, img_data[1][:struct.calcsize(header_fmt)])
            raw_buffer = np.fromstring(img_data[1][32:], np.uint16)
        return raw_buffer, width, height

    def get_lima_image(self):
        image = self.video.getLastImage()
        if image.frameNumber() > -1:
            raw_buffer = image.buffer()
        return raw_buffer, image.width(), image.height()

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
                return qimage.convertToFormat(QtGui.QImage.Format_Mono)
            else:
                return qimage

    def get_contrast(self):
        return

    def set_contrast(self, contrast_value):
        return

    def get_brightness(self):
        return

    def set_brightness(self, brightness_value):
        return

    def get_gain(self):
        if self.cam_type == "basler":
            if self.is_tango():
                value = self.device.video_gain
            else:
                value = self.video.getGain()
            return value

    def set_gain(self, gain_value):
        if self.cam_type == "basler":
            if self.is_tango():
                self.device.video_gain = gain_value
            else:
                value = self.video.setGain(gain_value)
            return

    def get_gamma(self):
        return

    def set_gamma(self, gamma_value):
        return

    def get_exposure_time(self):
        if self.cam_type == "basler":
            if self.is_tango():
                value = self.device.video_exposure
            else:
                value = self.video.getExposure()
            return value

    def set_exposure_time(self, exposure_time_value):
        #if self.is_tango():
            #self.device.video_exposure = exposure_time_value
        #else:
            #self.video.setExposure(exposure_time_value)
        return

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            if self.is_tango():
                self.device.video_mode = "YUV422"
            else:
                self.video.setMode(Core.YUV422)
            self.decoder = self.yuv_2_rgb
        elif cam_encoding == "y8":
            if self.is_tango():
                self.device.video_mode = "Y8"
            else:
                self.video.setMode(Core.Y8)
            self.decoder = self.y8_2_rgb
        return

    def get_video_live(self):
        if self.is_tango():
            return self.device.video_live 
        else:
            return self.video.getLive()
        return

    def set_video_live(self, flag):
        if self.is_tango():
            self.device.video_live = flag
        else:
            if flag is True:
                self.video.startLive()
            else:
                self.video.stopLive()

        return

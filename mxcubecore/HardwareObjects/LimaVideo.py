"""
Lima video HO to capture images from camera
Example xml:
<device class="LimaVideo">
   <type>prosilica</type>
   <address>169.254.1.3</address>
   <mirror>(True, False)</mirror>
   <scaleFactor>1.5</scaleFactor>
   <imageType>rgb</imageType>
   <interval>40</interval>
</device>
"""
import os
import time
import logging
import gevent

from Lima import Core
from Lima import Prosilica

from Qub.CTools import pixmaptools
from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.HardwareObjects.Camera import (
    JpegType,
    BayerType,
    MmapType,
    RawType,
    RGBType,
)


class LimaVideo(Device):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        Device.__init__(self, name)
        self.scaling = None
        self.scaling_type = None
        self.do_scaling = None
        self.force_update = None
        self.cam_type = None
        self.cam_address = None
        self.cam_mirror = None

        self.brightness_exists = None
        self.contrast_exists = None
        self.gain_exists = None
        self.gamma_exists = None

        self.image_format = None
        self.image_dimensions = [None, None]

        self.camera = None
        self.interface = None
        self.control = None
        self.video = None

        self.image_polling = None

    def init(self):
        """
        Descript. :
        """
        self.force_update = False
        self.scaling = pixmaptools.LUT.Scaling()
        self.cam_type = self.getProperty("type").lower()
        self.cam_address = self.getProperty("address")
        self.cam_mirror = eval(self.getProperty("mirror"))

        if self.cam_type == "prosilica":
            from Lima import Prosilica

            self.camera = Prosilica.Camera(self.cam_address)
            self.interface = Prosilica.Interface(self.camera)
        if self.cam_type == "ueye":
            from Lima import Ueye

            self.camera = Ueye.Camera(self.cam_address)
            self.interface = Ueye.Interface(self.camera)
        try:
            self.control = Core.CtControl(self.interface)
            self.video = self.control.video()
            self.image_dimensions = list(self.camera.getMaxWidthHeight())
        except KeyError:
            logging.getLogger().warning("Lima video not initialized.")

        self.setImageTypeFromXml("imageType")
        self.setIsReady(True)

        if self.image_polling is None:
            self.video.startLive()
            self.change_owner()

            self.image_polling = gevent.spawn(
                self.do_image_polling, self.getProperty("interval") / 1000.0
            )

    def setImageTypeFromXml(self, property_name):
        """
        Descript. :
        """
        image_format = self.getProperty(property_name) or "Jpeg"
        if image_format.lower() == "jpeg":
            self.image_format = JpegType()
        elif image_format.lower().startswith("bayer:"):
            self.image_format = BayerType(image_format.split(":")[1])
            if image_format.lower() == "bayer:8":
                self.scaling_type = pixmaptools.LUT.Scaling.BAYER_RG8
            elif image_format.lower() == "bayer:16":
                self.scaling_type = pixmaptools.LUT.Scaling.BAYER_RG16
        elif image_format.lower().startswith("y:"):
            self.image_format = BayerType(image_format.split(":")[1])
            if image_format.lower() == "y:8":
                self.scaling_type = pixmaptools.LUT.Scaling.Y8
        elif image_format.lower().startswith("raw"):
            self.image_format = RawType()
        elif image_format.lower() == "rgb":
            self.image_format = RGBType()
            self.scaling_type = pixmaptools.LUT.Scaling.RGB24
        elif image_format.lower().startswith("mmap:"):
            self.image_format = MmapType(image_format.split(":")[1])

    def imageType(self):
        """
        Descript. : returns image type
        """
        return self.image_format

    # ############   CONTRAST   #################
    def contrastExists(self):
        """
        Descript. :
        """
        return self.contrast_exists

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

    # ############   BRIGHTNESS   #################
    def brightnessExists(self):
        """
        Descript. :
        """
        return self.brightness_exists

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

    # ############   GAIN   #################
    def gainExists(self):
        """
        Descript. :
        """
        return self.gain_exists

    def setGain(self, gain):
        """
        Descript. :
        """
        return
        # self.video.setGain(gain)

    def getGain(self):
        """
        Descript. :
        """
        return self.video.getGain()

    def getGainMinMax(self):
        """
        Descript. :
        """
        return

    # ############   GAMMA   #################
    def gammaExists(self):
        """
        Descript. :
        """
        return self.gamma_exists

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

        if mode:
            self.video.startLive()
            self.change_owner()
        else:
            self.video.stopLive()

    def change_owner(self):
        """
        Descript. :
        """
        if os.getuid() == 0:
            try:
                os.setgid(int(os.getenv("SUDO_GID")))
                os.setuid(int(os.getenv("SUDO_UID")))
            except BaseException:
                logging.getLogger().warning(
                    "%s: failed to change the process ownership.", self.name()
                )

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

    def do_image_polling(self, sleep_time):
        """
        Descript. :
        """
        self.do_scaling = True
        while self.video.getLive():
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
        self.do_scaling = True

    def get_new_image(self):
        """
        Descript. :
        """
        image = self.video.getLastImage()
        if image.frameNumber() > -1:
            raw_buffer = image.buffer()
            if self.do_scaling:
                self.scaling.autoscale_min_max(
                    raw_buffer, image.width(), image.height(), self.scaling_type
                )
                self.do_scaling = False
            valid_flag, qimage = pixmaptools.LUT.raw_video_2_image(
                raw_buffer,
                image.width(),
                image.height(),
                self.scaling_type,
                self.scaling,
            )
            if valid_flag:
                if self.cam_mirror is not None:
                    qimage = qimage.mirror(self.cam_mirror[0], self.cam_mirror[1])
                self.emit(
                    "imageReceived",
                    qimage,
                    qimage.width(),
                    qimage.height(),
                    self.force_update,
                )
                return qimage

    def take_snapshot(self, filename, bw=False):
        """
        Descript. :
        """
        try:
            qimage = self.get_new_image()
            # TODO convert to grayscale
            # if bw:
            #    qimage.setNumColors(0)
            qimage.save(filename, "PNG")
        except BaseException:
            logging.getLogger().error(
                "LimaVideo: unable to save snapshot: %s" % filename
            )

"""
[Name] VaporyVideo

[Description]
Hardware object to simulate video with loop object. Hardware object is based
on a LimaVideo hardware object. It contains SimulatedLoop class that could
be used to display and navigate loop.
At this version vapory generates image each second and stores in /tmp.
At first look there is no direct conversion from vapory scene to qimage.

[Channels]

[Commands]

[Emited signals]

 - imageReceived : emits qimage to bricks

[Included Hardware Objects]
"""


import time
import gevent
import vapory
from gui.utils.QtImport import QImage
from mxcubecore import BaseHardwareObjects
from mxcubecore.hardware_objects.Camera import JpegType


class VaporyVideo(BaseHardwareObjects.Device):
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
        self.vapory_camera = vapory.Camera("location", [0, 2, -3], "look_at", [0, 1, 2])
        self.vapory_light = vapory.LightSource([2, 4, -3], "color", [1, 1, 1])

        self.simulated_loop = SimulatedLoop()
        self.simulated_loop.set_position(0, 0, 0)

        self.force_update = False
        self.image_dimensions = [600, 400]
        self.image_type = JpegType()
        self.set_is_ready(True)
        self.generate_image()

        self.image_polling = gevent.spawn(self._do_imagePolling, 1)

    def rotate_scene_absolute(self, angle):
        self.simulated_loop.set_position(angle, 0, 0)
        self.generate_image()

    def rotate_scene_relative(self, angle):
        return

    def generate_image(self):
        self.vapory_sene = vapory.Scene(
            self.vapory_camera,
            objects=[self.vapory_light, self.simulated_loop.loop_object],
        )
        image_array = self.vapory_sene.render(
            "/tmp/vapory_tmp_image.png",
            width=self.image_dimensions[0],
            height=self.image_dimensions[1],
        )
        self.qimage = QImage("/tmp/vapory_tmp_image.png")
        self.emit(
            "imageReceived",
            self.qimage,
            self.qimage.width(),
            self.qimage.height(),
            self.force_update,
        )

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
        while True:
            image_array = self.vapory_sene.render(
                "/tmp/vapory_tmp_image.png",
                width=self.image_dimensions[0],
                height=self.image_dimensions[1],
            )
            self.qimage = QImage("/tmp/vapory_tmp_image.png")
            self.emit(
                "imageReceived",
                self.qimage,
                self.qimage.width(),
                self.qimage.height(),
                self.force_update,
            )
            time.sleep(sleep_time)


class SimulatedLoop:
    def __init__(self):
        self.texture = vapory.Texture(vapory.Pigment("color", [1, 0, 1]))
        self.loop_object = vapory.Box([0, 0, 0], 2, self.texture)

    def set_position(self, x, y, z):
        self.loop_object.args = [[x, y, z], 2, self.texture]

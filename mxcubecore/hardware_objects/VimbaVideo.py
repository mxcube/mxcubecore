import time
import atexit
import numpy as np
from pymba import *

try:
    import cv2
except ImportError:
    pass

from gui.utils.QtImport import QImage, QPixmap
from mxcubecore.hardware_objects.abstract.AbstractVideoDevice import (
    AbstractVideoDevice,
)

from abstract.AbstractVideoDevice import AbstractVideoDevice


class VimbaVideo(AbstractVideoDevice):
    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)

        self.camera = None
        self.camera_index = 0
        self.qimage = None
        self.qpixmap = None
        self.use_qt = False
        self.raw_image_dimensions = [1360, 1024]

    def init(self):
        # start Vimba
        self.camera_index = self.get_property("camera_index", 0)
        self.use_qt = self.get_property("use_qt", True)

        atexit.register(self.close_camera)
        AbstractVideoDevice.init(self)

    def get_raw_image_size(self):
        return self.raw_image_dimensions

    def do_image_polling(self, sleep_time):
        with Vimba() as vimba:
            system = vimba.getSystem()

            if system.GeVTLIsPresent:
                system.runFeatureCommand("GeVDiscoveryAllOnce")
                time.sleep(0.2)
            cameraIds = vimba.getCameraIds()

            # self.camera = vimba.getCamera(self.camera_id)
            self.camera = vimba.getCamera(cameraIds[self.camera_index])
            self.camera.openCamera(cameraAccessMode=2)
            self.camera.framerate = 1
            self.frame0 = self.camera.getFrame()  # creates a frame
            self.frame0.announceFrame()
            self.camera.startCapture()

            self.raw_image_dimensions = (self.frame0.width, self.frame0.height)

            while True:
                self.frame0.waitFrameCapture(1000)
                self.frame0.queueFrameCapture()

                if self.use_qt:
                    self.qimage = QImage(
                        self.frame0.getBufferByteData(),
                        self.raw_image_dimensions[0],
                        self.raw_image_dimensions[1],
                        QImage.Format_RGB888,
                    )
                    if self.cam_mirror is not None:
                        self.qimage = self.qimage.mirrored(
                            self.cam_mirror[0], self.cam_mirror[1]
                        )
                    if self.qpixmap is None:
                        self.qpixmap = QPixmap(self.qimage)
                    else:
                        self.qpixmap.convertFromImage(self.qimage)
                    self.emit("imageReceived", self.qpixmap)
                else:
                    image_data = np.ndarray(
                        buffer=self.frame0.getBufferByteData(),
                        dtype=np.uint8,
                        shape=(
                            self.frame0.height,
                            self.frame0.width,
                            self.frame0.pixel_bytes,
                        ),
                    )
                    image_data = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGBA)
                    ret, im = cv2.imencode(".jpg", image_data)
                    self.emit(
                        "imageReceived",
                        im.tostring(),
                        self.frame0.width,
                        self.frame0.height,
                    )

                time.sleep(sleep_time)

    def get_new_image(self):
        return self.qimage

    def get_video_live(self):
        return True

    def close_camera(self):
        with Vimba() as vimba:
            self.camera.flushCaptureQueue()
            self.camera.endCapture()
            self.camera.revokeAllFrames()
            vimba.shutdown()

    def start_camera(self):
        pass

    def change_owner(self):
        pass

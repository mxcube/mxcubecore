import time
import gevent
import atexit
from pymba import *
from PyQt4.QtGui import QImage, QPixmap

from abstract.AbstractVideoDevice import GenericVideoDevice


class Qt4_VimbaVideo(AbstractVideoDevice):
    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)

        self.camera = None
        self.camera_id = str
        self.qimage = None
        self.qpixmap = None

    def init(self):
        # start Vimba
        self.camera_id = u"%s" % self.getProperty("camera_id")
        atexit.register(self.close_camera)
        AbstractVideoDevice.init(self)
        self.image_dimensions = [1360, 1024]

    def do_image_polling(self, sleep_time):
        with Vimba() as vimba:
            system = vimba.getSystem()

            if system.GeVTLIsPresent:
                system.runFeatureCommand("GeVDiscoveryAllOnce")
                time.sleep(0.2)
            cameraIds = vimba.getCameraIds()

            # self.camera = vimba.getCamera(self.camera_id)
            self.camera = vimba.getCamera(cameraIds[-1])
            self.camera.openCamera(cameraAccessMode=2)
            self.camera.framerate = 1
            self.frame0 = self.camera.getFrame()  # creates a frame
            self.frame0.announceFrame()
            self.camera.startCapture()

            self.image_dimensions = (self.frame0.width, self.frame0.height)

            while True:
                self.frame0.waitFrameCapture(1000)
                self.frame0.queueFrameCapture()
                self.qimage = QImage(
                    self.frame0.getBufferByteData(),
                    self.image_dimensions[0],
                    self.image_dimensions[1],
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

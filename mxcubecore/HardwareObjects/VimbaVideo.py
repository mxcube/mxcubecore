import time
import atexit
import numpy as np
from pymba import *

try:
    import cv2
except ImportError:
    pass

from mxcubecore.utils.qt_import import QImage, QPixmap
from mxcubecore.HardwareObjects.abstract.AbstractVideoDevice import (
    AbstractVideoDevice,
)

from abstract.AbstractVideoDevice import AbstractVideoDevice


class VimbaVideo(AbstractVideoDevice):
    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)

        self.camera = None
        self.camera_id = None
        self.qimage = None
        self.qpixmap = None
        self.use_qt = False
        self.raw_image_dimensions = [1360, 1024]

    def init(self):
        # start Vimba
        self.camera_id = self.get_property("camera_id")
        self.use_qt = self.get_property("use_qt", True)

        atexit.register(self.close_camera)
        AbstractVideoDevice.init(self)

    def get_raw_image_size(self):
        return self.raw_image_dimensions

    def do_image_polling(self, sleep_time):
        with Vimba() as vimba:
            self.camera = vimba.camera(self.camera_id)
            self.camera.open(camera_access_mode=2, adjust_packet_size=False)
            self.frame = self.camera.new_frame()
            self.frame.announce()
            self.camera.start_capture()

            self.raw_image_dimensions = (
                self.camera.feature("Width").value,
                self.camera.feature("Height").value
            )
            
            while True:
                self.frame.wait_for_capture(1000)
                self.frame.queue_for_capture()

                if self.use_qt:
                    self.qimage = QImage(
                        self.frame.buffer_data(),
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
                    image_data = cv2.cvtColor(
                        self.frame.buffer_data_numpy(),
                        cv2.COLOR_BGR2RGBA
                    )
                    ret, im = cv2.imencode(".jpg", image_data)
                    self.emit(
                        "imageReceived",
                        im.tostring(),
                        self.frame.width,
                        self.frame.height,
                    )

                time.sleep(sleep_time)

    def get_new_image(self):
        return self.qimage

    def get_video_live(self):
        return True

    def close_camera(self):
        with Vimba() as vimba:
            self.camera.flush_capture_queue()
            self.camera.end_capture()
            self.camera.revoke_all_frames()
            vimba.shutdown()

    def start_camera(self):
        pass

    def change_owner(self):
        pass

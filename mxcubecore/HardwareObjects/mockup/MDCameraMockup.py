"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
import psutil
import subprocess
import logging
import time
import gevent

from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR

MAX_TRIES = 3
SLOW_INTERVAL = 1000


class MDCameraMockup(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def _init(self):
        self.stream_hash = "abc123"
        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False
        self.image_name = self.get_property("image_name")
        self.image = HWR.get_hardware_repository().find_in_repository(self.image_name)
        self.set_is_ready(True)
        self._video_stream_process = None

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False  # self.polling_timer(self.pollInterval, self.poll)
        gevent.spawn(self.poll)

    def udiffVersionChanged(self, value):
        if value == "MD2_2":
            print(("start polling MD camera with poll interval=", self.pollInterval))
        else:
            print(
                "stop polling the camera. This microdiff version does not support a camera"
            )
            self.stopper = True

    def connectToDevice(self):
        self.connected = True
        return self.connected

    def poll(self):
        logging.getLogger("HWR").info("going to poll images")
        while not self.stopper:
            time.sleep(1)
            try:
                img = open(self.image, "rb").read()
                self.emit("imageReceived", img, 659, 493)
            except Exception:
                logging.getLogger("HWR").exception("Could not read image")

    def imageUpdated(self, value):
        print("<HW> got new image")
        print(value)

    def gammaExists(self):
        return False

    def contrastExists(self):
        return False

    def brightnessExists(self):
        return False

    def gainExists(self):
        return False

    def get_width(self):
        # return 768 #JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659

    def get_height(self):
        # return 576 # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def set_live(self, state):
        self.liveState = state
        return True

    def imageType(self):
        return None

    def takeSnapshot(self, snapshot_filename, bw=True):
        return True

    take_snapshot = takeSnapshot

    def get_available_stream_sizes(self):
        return [(self.get_width(), self.get_height())]

    def get_stream_size(self):
        return self.get_width(), self.get_height(), 1

    def start_video_stream_process(self, format):
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            self._video_stream_process = subprocess.Popen(
                [
                    "video-streamer",
                    "-tu",
                    "test",
                    "-hs",
                    "localhost",
                    "-p",
                    "8000",
                    "-of",
                    format,
                    "-q",
                    "4",
                    "-id",
                    self.stream_hash,
                ],
                close_fds=True,
            )

    def stop_streaming(self):
        if self._video_stream_process:
            ps = [self._video_stream_process] + psutil.Process(
                self._video_stream_process.pid
            ).children()
            for p in ps:
                p.kill()
            self._video_stream_process = None

    def start_streaming(self, format="MPEG1"):
        self.start_video_stream_process(format)

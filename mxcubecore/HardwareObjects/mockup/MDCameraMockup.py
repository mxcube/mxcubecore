"""Class for cameras connected to framegrabbers run by Taco Device Servers"""

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
        self._format = "MPEG1"
        self.stream_hash = "abc123"
        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False
        self.image_name = self.get_property("image_name")
        self.image = HWR.get_hardware_repository().find_in_repository(self.image_name)
        self.set_is_ready(True)
        self._video_stream_process = None
        self._current_stream_size = "0, 0"

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
        try:
            w, h = self.get_width(), self.get_height()
            video_sizes = [(w, h), (int(w / 2), int(h / 2)), (int(w / 4), int(h / 4))]
        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def set_stream_size(self, w, h):
        self._current_stream_size = "%s,%s" % (int(w), int(h))

    def get_stream_size(self):
        current_size = self._current_stream_size.split(",")
        scale = float(current_size[0]) / self.get_width()
        return current_size + list((scale,))

    def start_video_stream_process(self, port):
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            self._video_stream_process = subprocess.Popen(
                [
                    "video-streamer",
                    "-uri",
                    "test",
                    "-hs",
                    "localhost",
                    "-p",
                    str(self._port),
                    "-of",
                    self._format,
                    "-q",
                    "4",
                    "-s",
                    self._current_stream_size,
                    "-id",
                    self.stream_hash,
                ],
                close_fds=True,
            )

    def stop_streaming(self):
        if self._video_stream_process:
            try:
                ps = [self._video_stream_process] + psutil.Process(
                    self._video_stream_process.pid
                ).children()
                for p in ps:
                    p.kill()
            except psutil.NoSuchProcess:
                pass

            self._video_stream_process = None

    def start_streaming(self, _format="MPEG1", size=(0, 0), port="8000"):
        self._format = _format
        self._port = port

        if not size[0]:
            _s = int(self.get_width()), int(self.get_height())
        else:
            _s = int(size[0]), int(size[1])

        self.set_stream_size(_s[0], _s[1])
        self.start_video_stream_process(port)

    def restart_streaming(self, size):
        self.stop_streaming()
        self.start_streaming(self._format, size=size)

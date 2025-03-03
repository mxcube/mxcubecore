"""Class for cameras connected to framegrabbers run by Taco Device Servers"""

import atexit
import logging
import os
import signal
import subprocess
import time
from typing import (
    List,
    Tuple,
)

import gevent
import psutil
from PIL import Image

from mxcubecore import BaseHardwareObjects
from mxcubecore import HardwareRepository as HWR

MAX_TRIES = 3
SLOW_INTERVAL = 1000


class MDCameraMockup(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        super().__init__(name)

    def _init(self):
        self._format = "MPEG1"
        self.stream_hash = "abc123"
        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False
        self.image_name = self.get_property("image_name")
        self.image = HWR.get_hardware_repository().find_in_repository(self.image_name)
        self.update_state(BaseHardwareObjects.HardwareObjectState.READY)
        self._video_stream_process = None
        self._current_stream_size = (0, 0)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False  # self.polling_timer(self.pollInterval, self.poll)
        gevent.spawn(self.poll)

    def udiffVersionChanged(self, value) -> None:
        if value == "MD2_2":
            print(("start polling MD camera with poll interval=", self.pollInterval))
        else:
            print(
                "stop polling the camera. This microdiff version does not support a camera"
            )
            self.stopper = True

    def connectToDevice(self) -> bool:
        self.connected = True
        return self.connected

    def poll(self) -> None:
        logging.getLogger("HWR").info("going to poll images")
        while not self.stopper:
            time.sleep(1)
            try:
                img = open(self.image, "rb").read()
                self.emit("imageReceived", img, 659, 493)
            except Exception:
                logging.getLogger("HWR").exception("Could not read image")

    def imageUpdated(self, value) -> None:
        print("<HW> got new image")
        print(value)

    def gammaExists(self) -> bool:
        return False

    def contrastExists(self) -> bool:
        return False

    def brightnessExists(self) -> bool:
        return False

    def gainExists(self) -> bool:
        return False

    def get_width(self) -> int:
        # return 768 #JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659

    def get_height(self) -> int:
        # return 576 # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def set_live(self, state) -> bool:
        self.liveState = state
        return True

    def get_last_image(self) -> Tuple[bytes, int, int]:
        image = Image.open(self.image)
        return image.tobytes(), image.size[0], image.size[1]

    def get_available_stream_sizes(self) -> List[Tuple[int, int]]:
        try:
            w, h = self.get_width(), self.get_height()
            video_sizes = [(w, h), (int(w / 2), int(h / 2)), (int(w / 4), int(h / 4))]
        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def set_stream_size(self, w, h) -> None:
        self._current_stream_size = (int(w), int(h))

    def get_stream_size(self) -> Tuple[int, int, float]:
        width, height = self._current_stream_size
        scale = float(width) / self.get_width()
        return (width, height, scale)

    def clean_up(self):
        logging.getLogger("HWR").info("Shutting down video_stream...")
        os.kill(self._video_stream_process.pid, signal.SIGTERM)

    def start_video_stream_process(self) -> None:
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
                    ", ".join(map(str, self._current_stream_size)),
                    "-id",
                    self.stream_hash,
                ],
                close_fds=True,
                stdout=subprocess.DEVNULL,
            )

            atexit.register(self.clean_up)

    def stop_streaming(self) -> None:
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

    def start_streaming(self, _format="MPEG1", size=(0, 0), port="8000") -> None:
        self._format = _format
        self._port = port

        if not size[0]:
            _s = int(self.get_width()), int(self.get_height())
        else:
            _s = int(size[0]), int(size[1])

        self.set_stream_size(_s[0], _s[1])
        self.start_video_stream_process()

    def restart_streaming(self, size) -> None:
        self.stop_streaming()
        self.start_streaming(self._format, size=size)

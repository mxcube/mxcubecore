"""
Class for streaming MPEG1 video with cameras connected to
Lima Tango Device Servers

Example configuration:

<object class="TangoLimaMpegVideo">
  <username>Prosilica 1350C</username>
  <tangoname>id23/limaccd/minidiff</tangoname>
  <bpmname>id23/limabeamviewer/minidiff</bpmname>
  <exposure_time>0.05</exposure_time>
  <video_mode>RGB24</video_mode>
</object>
"""

import atexit
import logging
import os
import signal
import subprocess
import uuid
from typing import (
    List,
    Tuple,
)

import psutil

from mxcubecore.HardwareObjects.TangoLimaVideo import TangoLimaVideo


class TangoLimaMpegVideo(TangoLimaVideo):
    def __init__(self, name):
        super(TangoLimaMpegVideo, self).__init__(name)
        self._format = "MPEG1"
        self._video_stream_process = None
        self._current_stream_size = (0, 0)
        self.stream_hash = str(uuid.uuid1())
        self._quality_str = "High"
        self._QUALITY_STR_TO_INT = {"High": 4, "Medium": 10, "Low": 20, "Adaptive": -1}
        self._port = 8000

    def init(self):
        super().init()
        self._debug = self.get_property("debug", False)
        self._quality = self.get_property("compression", 10)
        self._mpeg_scale = self.get_property("mpeg_scale", 1)
        self._image_size = (self.get_width(), self.get_height())

    def get_quality(self) -> str:
        return self._quality_str

    def set_quality(self, q) -> None:
        self._quality_str = q
        self._quality = self._QUALITY_STR_TO_INT[q]
        self.restart_streaming()

    def set_stream_size(self, w, h) -> None:
        self._current_stream_size = (int(w), int(h))

    def get_stream_size(self) -> Tuple[int, int, float]:
        width, height = self._current_stream_size
        scale = float(width) / self.get_width()
        return (width, height, scale)

    def get_quality_options(self) -> List[str]:
        return list(self._QUALITY_STR_TO_INT.keys())

    def get_available_stream_sizes(self) -> List[Tuple[int, int]]:
        try:
            w, h = self.get_width(), self.get_height()
            video_sizes = [(w, h), (int(w / 2), int(h / 2)), (int(w / 4), int(h / 4))]
        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def clean_up(self) -> None:
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
                    self.get_property("tangoname").strip(),
                    "-hs",
                    "localhost",
                    "-p",
                    str(self._port),
                    "-q",
                    str(self._quality),
                    "-s",
                    ", ".join(map(str, self._current_stream_size)),
                    "-of",
                    self._format,
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

    def start_streaming(self, _format=None, size=(0, 0), port=None) -> None:
        if _format:
            self._format = _format

        if port:
            self._port = port

        if not size[0]:
            _s = self.get_width(), self.get_height()
        else:
            _s = size

        self.set_stream_size(_s[0], _s[1])
        self.start_video_stream_process()

    def restart_streaming(self, size) -> None:
        self.stop_streaming()
        self.start_streaming(self._format, size=size)

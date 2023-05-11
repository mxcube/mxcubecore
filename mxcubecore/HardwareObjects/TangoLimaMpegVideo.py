"""
Class for streaming MPEG1 video with cameras connected to 
Lima Tango Device Servers

Example configuration:

<device class="TangoLimaMpegVideo">
  <username>Prosilica 1350C</username>
  <tangoname>id23/limaccd/minidiff</tangoname>
  <bpmname>id23/limabeamviewer/minidiff</bpmname>
  <exposure_time>0.05</exposure_time>
  <video_mode>RGB24</video_mode>
</device>
"""
import os
import subprocess
import uuid
import psutil

from mxcubecore.HardwareObjects.TangoLimaVideo import TangoLimaVideo


class TangoLimaMpegVideo(TangoLimaVideo):
    def __init__(self, name):
        super(TangoLimaMpegVideo, self).__init__(name)
        self._format = "MPEG1"
        self._video_stream_process = None
        self._current_stream_size = "0, 0"
        self.stream_hash = str(uuid.uuid1())
        self._quality_str = "High"
        self._QUALITY_STR_TO_INT = {"High": 4, "Medium": 10, "Low": 20, "Adaptive": -1}

    def init(self):
        super().init()
        self._debug = self.get_property("debug", False)
        self._quality = self.get_property("compression", 10)
        self._mpeg_scale = self.get_property("mpeg_scale", 1)
        self._image_size = (self.get_width(), self.get_height())

    def get_quality(self):
        return self._quality_str

    def set_quality(self, q):
        self._quality_str = q
        self._quality = self._QUALITY_STR_TO_INT[q]
        self.restart_streaming()

    def set_stream_size(self, w, h):
        self._current_stream_size = "%s,%s" % (int(w), int(h))

    def get_stream_size(self):
        current_size = self._current_stream_size.split(",")
        scale = float(current_size[0]) / self.get_width()
        return current_size + list((scale,))

    def get_quality_options(self):
        return list(self._QUALITY_STR_TO_INT.keys())

    def get_available_stream_sizes(self):
        try:
            w, h = self.get_width(), self.get_height()
            video_sizes = [(w, h), (int(w / 2), int(h / 2)), (int(w / 4), int(h / 4))]
        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def start_video_stream_process(self, port):
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            self._video_stream_process = subprocess.Popen(
                [
                    "video-streamer",
                    "-tu",
                    self.get_property("tangoname").strip(),
                    "-hs",
                    "localhost",
                    "-p",
                    port,
                    "-q",
                    str(self._quality),
                    "-s",
                    self._current_stream_size,
                    "-of",
                    self._format,
                    "-id",
                    self.stream_hash,
                ],
                close_fds=True,
            )

            with open("/tmp/mxcube.pid", "a") as f:
                f.write("%s " % self._video_stream_process.pid)

    def stop_streaming(self):
        if self._video_stream_process:
            ps = psutil.Process(self._video_stream_process.pid).children() + [
                self._video_stream_process
            ]

            for p in ps:
                p.kill()

            self._video_stream_process = None

    def start_streaming(self, fmt=None, size=(0, 0)):
        if fmt:
            self._format = fmt

        if not size[0]:
            _s = self.get_width(), self.get_height()
        else:
            _s = size

        self.set_stream_size(_s[0], _s[1])
        self.start_video_stream_process()

    def restart_streaming(self, size):
        self.stop_streaming()
        self.start_streaming(self._format)

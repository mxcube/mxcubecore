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
import logging
import os
import subprocess
import uuid
import psutil

from mxcubecore.HardwareObjects.TangoLimaVideo import TangoLimaVideo
from mxcubecore.utils.video_utils import streaming_processes


class TangoLimaMpegVideo(TangoLimaVideo):
    def __init__(self, name):
        super(TangoLimaMpegVideo, self).__init__(name)

        self._video_stream_process = None
        self._current_stream_size = "-1, -1"
        self._stream_script_path = ""
        self.stream_hash = str(uuid.uuid1())
        self.video_device = None
        self._p = None
        self._quality_str = "High"
        self._QUALITY_STR_TO_INT = {
            "High": 4,
            "Medium": 10,
            "Low": 20,
            "Adaptive": -1
        }

    def init(self):
        super().init()
        self._debug = self.get_property("debug", False)
        self._loopback_device = self.get_property("loopback_device", "")
        self._quality = self.get_property("compression", 10)
        self._mpeg_scale = self.get_property("mpeg_scale", 1)
    def _encoder_friendly_size(self, w, h):
        # Some video decoders have difficulties to decode videos with odd image dimensions
        # (JSMPEG beeing one of them) so we make sure that the size is even
        w = w if w % 2 == 0 else w + 1
        h = h if h % 2 == 0 else h + 1

        return w, h

    def get_quality(self):
        return self._quality_str

    def set_quality(self, q):
        self._quality_str = q
        self._quality = self._QUALITY_STR_TO_INT[q]
        self.restart_streaming()

    def set_stream_size(self, w, h):
        w, h = self._encoder_friendly_size(w, h)
        self._current_stream_size = "%s,%s" % (int(w), int(h))

    def get_stream_size(self):
        current_size = self._current_stream_size.split(",")
        scale = float(current_size[0]) / self.get_width()
        return current_size + list((scale,))

    def get_quality_options(self):
        return list(self._QUALITY_STR_TO_INT.keys())

    def get_available_stream_sizes(self):
        try:
            w, h = self._encoder_friendly_size(self.get_width(), self.get_height())
            # Calculate half the size and quarter of the size if MPEG streaming is used
            # otherwise just return the orignal size.
            if self._video_stream_process:
                video_sizes = [(w, h), (w / 2, h / 2), (w / 4, h / 4)]
            else:
                video_sizes = [(w, h)]

        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def start_video_stream_process(self):
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            python_executable = os.sep.join(
                os.path.dirname(os.__file__).split(os.sep)[:-2] + ["bin", "python"]
            )

            self._video_stream_process = subprocess.Popen(
                [
                    "video-streamer",
                    "-d", self.get_property("tangoname").strip(),
                    "-b", "localhost",
                    "-p", "4042",
                    "-q", str(self._quality),
                    "-hs", self.stream_hash
                ],
                stdin=subprocess.PIPE,
                shell=False,
                close_fds=True,
            )

            with open("/tmp/mxcube.pid", "a") as f:
                f.write("%s " % self._video_stream_process.pid)

    def stop_streaming(self):
        if self._video_stream_process:
            ps = [self._video_stream_process] + psutil.Process(
                self._video_stream_process.pid
            ).children()
            for p in ps:
                p.kill()
            self._video_stream_process = None

    def start_streaming(self, size=()):
        if not size:
            w, h = self.get_width(), self.get_height()
        else:
            w, h = size

        self.set_stream_size(w * self._mpeg_scale, h * self._mpeg_scale)
        self.start_video_stream_process()

        return self.video_device

    def restart_streaming(self, size=()):
        self.stop_streaming()
        self.start_streaming(size)

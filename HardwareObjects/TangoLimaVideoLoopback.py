"""Class for cameras connected to Lima Tango Device Servers

Example configuration:
----------------------
<device class="TangoLimaVideo">
  <username>Prosilica 1350C</username>
  <tangoname>id23/limaccd/minidiff2</tangoname>
  <bpmname>id23/limabeamviewer/minidiff2</bpmname>
  <interval>15</interval>
  <video_mode>RGB24</video_mode>
</device>

If video mode is not specified, BAYER_RG16 is used by default.
"""
import logging
import v4l2
import gipc
import os
import fcntl
import subprocess
import time
import uuid
import gevent

from HardwareRepository.HardwareObjects.TangoLimaVideo import TangoLimaVideo, poll_image


def _poll_image(sleep_time, video_device, device_uri, video_mode, formats):
    from PyTango import DeviceProxy

    # lima_tango_device = PyTango.DeviceProxy(device_uri, timeout=10000)
    connected = False

    while not connected:
        try:
            logging.getLogger("HWR").info("Connecting to %s", device_uri)
            lima_tango_device = DeviceProxy(device_uri)
            lima_tango_device.ping()
        except Exception as ex:
            logging.getLogger("HWR").exception("")
            logging.getLogger("HWR").info(
                "Could not connect to %s, retrying ...", device_uri
            )
            time.sleep(0.1)
            connected = False
        else:
            connected = True

    while True:
        try:
            data = poll_image(lima_tango_device, video_mode, formats)[0]
            video_device.write(data)
        except:
            pass
        finally:
            time.sleep(sleep_time)


class TangoLimaVideoLoopback(TangoLimaVideo):
    def __init__(self, name):
        super(TangoLimaVideoLoopback, self).__init__(name)

        self._video_stream_process = None
        self._current_stream_size = "-1, -1"
        self._original_stream_size = -1, -1
        self._stream_script_path = ""
        self.stream_hash = str(uuid.uuid1())
        self.video_device = None
        self._polling_mode = "process"
        self._p = None

    def init(self):
        super(TangoLimaVideoLoopback, self).init()
        self._polling_mode = self.get_property("polling_mode", "process")

    def _do_polling(self, sleep_time):
        if self._polling_mode == "process":
            self._p = gipc.start_process(
                target=_poll_image,
                args=(
                    sleep_time,
                    self.video_device,
                    self.get_property("tangoname"),
                    self.video_mode,
                    self._FORMATS,
                ),
            )
        else:
            self._p = gevent.spawn(
                _poll_image,
                sleep_time,
                self.video_device,
                self.get_property("tangoname"),
                self.video_mode,
                self._FORMATS,
            )

    def _open_video_device(self, path="/dev/video0"):
        if os.path.exists(path):
            device = open(path, "wb", 0)
            self.video_device = device
        else:
            msg = "Cannot open video device %s, path do not exist. " % path
            msg += "Make sure that the v4l2loopback kernel module is loaded (modprobe v4l2loopback). "
            msg += "Falling back to MJPEG."
            raise RuntimeError(msg)

        return self.video_device

    def _initialize_video_device(self, pixel_format, width, height, channels):
        f = v4l2.v4l2_format()
        f.type = v4l2.V4L2_BUF_TYPE_VIDEO_OUTPUT
        f.fmt.pix.pixelformat = pixel_format
        f.fmt.pix.width = width
        f.fmt.pix.height = height
        f.fmt.pix.field = v4l2.V4L2_FIELD_NONE
        f.fmt.pix.bytesperline = width * channels
        f.fmt.pix.sizeimage = width * height * channels
        f.fmt.pix.colorspace = v4l2.V4L2_COLORSPACE_SRGB

        res = fcntl.ioctl(self.video_device, v4l2.VIDIOC_S_FMT, f)

        if res != 0:
            raise RuntimeError("Could not initialize video device: %d" % res)

        return True

    def _encoder_friendly_size(self, w, h):
        # Some video decoders have difficulties to decode videos with odd image dimensions
        # (JSMPEG beeing one of them) so we make sure that the size is even
        w = w if w % 2 == 0 else w + 1
        h = h if h % 2 == 0 else h + 1

        return w, h

    def set_stream_size(self, w, h):
        w, h = self._encoder_friendly_size(w, h)
        self._current_stream_size = "%s,%s" % (w, h)

    def _set_stream_original_size(self, w, h):
        w, h = self._encoder_friendly_size(w, h)
        self._original_stream_size = w, h

    def get_stream_size(self):
        current_size = self._current_stream_size.split(",")
        scale = float(current_size[0]) / self._original_stream_size[0]
        return current_size + list((scale,))

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
        if self._video_stream_process:
            self.stop_video_stream_process()

        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            python_executable = os.sep.join(
                os.path.dirname(os.__file__).split(os.sep)[:-2] + ["bin", "python"]
            )
            self._video_stream_process = subprocess.Popen(
                [
                    python_executable,
                    self._stream_script_path,
                    self.video_device.name,
                    self._current_stream_size,
                    self.stream_hash,
                ],
                close_fds=True,
            )

    def stop_video_stream_process(self):
        if self._video_stream_process:
            os.system("pkill -TERM -P {pid}".format(pid=self._video_stream_process.pid))
            self._video_stream_process = None

    def restart(self):
        self.start_video_stream_process()

    def start(self, loopback_device_path, stream_script_path):
        self._stream_script_path = stream_script_path
        w, h = self.get_width(), self.get_height()

        self._open_video_device(loopback_device_path)
        self._initialize_video_device(v4l2.V4L2_PIX_FMT_RGB24, w, h, 3)

        self.set_stream_size(w, h)
        self._set_stream_original_size(w, h)
        self.start_video_stream_process()

        self._do_polling(self.device.video_exposure)

        return self.video_device

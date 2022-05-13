import time
import gevent
# import array
import uuid
from mxcubecore.HardwareObjects.abstract.AbstractVideoDevice import AbstractVideoDevice
import logging
import PyTango
import struct
import io
from PIL import Image
# import numpy as np
import subprocess
import psutil
from mxcubecore.utils.video_utils import streaming_processes

"""
<device class="Arinax.TangoBzoomCamera">
  <username>bzoom</username>
  <tangoname>tango://tango_name</tangoname>
  <interval>40</interval>
  <image_channel>video_last_image</image_channel>
  <camera_video_mode>video_mode</camera_video_mode>
  <exposure_time>video_exposure</exposure_time>
  <gain_channel>video_gain</gain_channel>
  <video_width>image_width</video_width>
  <video_height>image_height</video_height>
  <scale_chan>video_scale</scale_chan>
  <type>bzoom</type>
  <encoding>rgb24</encoding>
  <scale>1</scale>
</device>
"""

__credits__ = ["Arinax"]

canTakeSnapshots = True


class TangoBzoomCamera(AbstractVideoDevice):

    def __init__(self, name):
        AbstractVideoDevice.__init__(self, name)
        self.stream_hash = str(uuid.uuid1())
        # self.__polling = None
        # Dictionary containing conversion information for a given
        # video_mode. The camera video mode is the key and the first
        # index of the tuple contains the corresponding PIL mapping
        # and the second the desried output format. The image is
        # passed on as it is of the video mode is not in the dictionary
        self._FORMATS = {
            "RGB8": "L",
            "RGB24": "RGB",
            "RGB32": "RGBA"
        }

    def _init(self):
        logging.getLogger("HWR").info("initializing camera object")
        tangoname = self.get_property("tangoname")
        self.device = PyTango.DeviceProxy(tangoname)
        # self.video_mode = self.add_channel(
        #     {"type": "tango", "name": "video_mode"}, self.get_property("camera_video_mode"))
        self.image_attr = self.add_channel(
            {"type": "tango", "name": "video_last_image"}, self.get_property("image_channel"))
        self.exposure = self.add_channel(
            {"type": "tango", "name": "exposure"}, self.get_property("exposure_time"))
        # self.gain = self.add_channel(
        #     {"type": "tango", "name": "gain"}, self.get_property("gain_channel"))
        self.width = self.add_channel(
            {"type": "tango", "name": "width"}, self.get_property("video_width"))
        self.height = self.add_channel(
            {"type": "tango", "name": "height"}, self.get_property("video_height"))
        self.scale_channel = self.add_channel(
            {"type": "tango", "name": "scale"}, self.get_property("scale_chan"))
        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False
        # self.camera_format = self.get_video_mode()
        self.camera_format = self.get_property("video_mode")
        # self.video_live = False
        self.cam_name = self.get_property("username")
        self._current_stream_size = "-1, -1"
        self._quality = self.get_property("compression", 10)
        self._debug = self.get_property("debug", False)
        self._mpeg_scale = 1
        self._video_stream_process = None


        AbstractVideoDevice.init(self)

    def get_video_mode(self):
        return self._FORMATS[self.video_mode.getValue()]

    """Implementation of Abstract methods"""

    def get_raw_image_size(self):
        return [self.width.get_value(), self.height.get_value()]

    def get_image(self):
        return self.image_attr.get_value()

    # def get_gain(self):
    #     return self.gain.get_value()
    #
    # def set_gain(self, gain_value):
    #     self.get_channel_object("gain").set_value(gain_value)

    def get_exposure_time(self):
        return self.exposure.get_value()

    def set_exposure_time(self, exposure_time_value):
        self.get_channel_object("exposure").set_value(exposure_time_value)

    def get_video_live(self):
        return False

    def set_video_live(self, flag):

        # self.video_live = flag
        return NotImplementedError

    """Overridden from AbstractVideoDevice"""

    def get_scaling_factor(self):
        return self.scale_channel.get_value()

    def get_image_bytes(self):
        img_data = self.get_image()
        hfmt = ">IHHqiiHHHH"
        hsize = struct.calcsize(hfmt)
        _, _, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
            hfmt, img_data[1][:hsize]
        )

        raw_data = img_data[1][hsize:]

        return raw_data, width, height

    def get_jpg_image(self):
        raw_data, width, height = self.get_image_bytes()
        img_byte = io.BytesIO()
        image = Image.frombytes(self.camera_format, (width, height), raw_data, "raw")
        image.save(img_byte, "JPEG")
        img = img_byte.getvalue()
        return img, width, height

    def take_snapshot(self, path=None, bw=False):
        raw_data, width, height = self.get_image_bytes()
        # img_byte = io.BytesIO()
        img = Image.frombytes(self.camera_format, (width, height), raw_data, "raw")
        # img_bytes = io.BytesIO()
        # img.save(img_bytes, format="BMP")
        # img = img.tobytes()

        # img = Image.frombytes("RGB", (width, height), data)

        if bw:
            img.convert("1")

        if path:
            img.save(path)

        return img

    def do_image_polling(self, sleep_time):
        while True:
            try:
                data, width, height = self.get_jpg_image()
                self._last_image = data, width, height
                self.emit("imageReceived", data, width, height, False)
                time.sleep(sleep_time)
            except Exception as ex:
                self.log.error("Exception while polling image from Tango Camera: ", ex)

    def connectNotify(self, signal):
        if signal == "imageReceived":
            if self.image_polling is None:
                self.image_polling = gevent.spawn(
                    self.do_image_polling, self.pollInterval / 1000  # tango export camera exposure in microseconds
                )

    def get_gamma(self):
        return NotImplementedError

    def set_gamma(self, gamma_value):
        return NotImplementedError

    def get_contrast(self):
        return NotImplementedError

    def set_contrast(self, contrast_value):
        return NotImplementedError

    def get_brightness(self):
        return NotImplementedError

    def set_brightness(self, brightness_value):
        return NotImplementedError

    def get_width(self):
        return self.width.get_value()

    def get_height(self):
        return self.height.get_value()

    ####### For MPEG stream ########

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
        # import pdb; pdb.set_trace()
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            # python_executable = os.sep.join(
            #     os.path.dirname(os.__file__).split(os.sep)[:-2] + ["bin", "python"]
            # )
            python_executable = "/home/arinax/mx3env_py3/bin/python3"

            self._video_stream_process = subprocess.Popen(
                [
                    python_executable,
                    streaming_processes.__file__,
                    self.get_property("tangoname"),
                    "%s, %s" % (self.get_width(), self.get_height()),
                    self._current_stream_size,
                    self.stream_hash,
                    "rgb24",
                    "",
                    str(self._debug),
                    str(self.pollInterval/1000.0),
                    str(self._quality)
                ],
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

        # return self.video_device

    def restart_streaming(self, size=()):
        self.stop_streaming()
        self.start_streaming(size)

def test_hwo(hwo):
    print("Video size: ", hwo.get_raw_image_size())
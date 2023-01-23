"""
Camera hardware object for Arinax MD3UP on-axis video microscope.

Implements the required API for displaying MD3UP microscope video stream in the UI.

Supported properties:

  tangoname (required) - name or full URL of the Arinax tango video device
  interval - frame polling interval, in milliseconds
"""
import uuid
import time
import tango
import struct
import gevent
import logging
from pathlib import Path
from io import BytesIO
from PIL import Image
from mxcubecore.BaseHardwareObjects import HardwareObject

log = logging.getLogger("HWR")

# default polling interval for video frames, in milliseconds
DEFAULT_POLL_INTERVAL = 50  # ~20 FPS

# monochrome, 8-bit per pixel
IMAGE_MODE_L = 0
# rgb, 24-bit per pixel
IMAGE_MODE_RGB = 6

MISSING_FRAME_WIDTH = 1224
MISSING_FRAME_HEIGHT = 1024
MISSING_FRAME_COLOR = "pink"


def _make_frame_missing_image() -> bytes:
    image = Image.new(
        "RGB", (MISSING_FRAME_WIDTH, MISSING_FRAME_HEIGHT), color=MISSING_FRAME_COLOR
    )
    buffer = BytesIO()
    image.save(buffer, "JPEG")

    return buffer.getvalue()


class MD3UpCamera(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        self.stream_hash = str(uuid.uuid1())
        self.device = None
        self._poll_images = False
        self._start_polling = gevent.event.Event()
        self._frame_missing_image = _make_frame_missing_image()

    def init(self):
        # calculate polling interval in seconds
        self._poll_interval = (
            self.get_property("interval", DEFAULT_POLL_INTERVAL) / 1000
        )
        self.device = tango.DeviceProxy(self.get_property("tangoname"))
        self.device.ping()
        gevent.spawn(self._poll)

    def get_image_zoom(self):
        # hard-coded to 1.0, for compatibility reasons
        return 1.0

    def get_width(self):
        return self.device.image_width

    def get_height(self):
        return self.device.image_height

    def connect_notify(self, signal):
        if signal != "imageReceived":
            # we only care about 'imageReceived' signal connections
            return

        # video client connected, start fetching images from MD3Up
        self._poll_images = True
        self._start_polling.set()

    def disconnect_notify(self, signal):
        if signal != "imageReceived":
            # we only care about 'imageReceived' signal connections
            return

        # video client disconnected, stop fetching images
        self._poll_images = False

    def take_snapshot(self, path, grayscale=False):
        _, _, jpg_data = self._get_jpg_image()
        Path(path).write_bytes(jpg_data)

    def _get_frame(self):
        """
        read one frame from tango device

        returns: frame's width, height, color mode and pixels,
        """
        _, frame = self.device.video_last_image

        (
            magic_number,
            version,
            image_mode,
            frame_number,
            width,
            height,
            endianness,
            header_size,
        ) = struct.unpack(">IHHqiiHH", frame[0:28])

        #
        # The MD3Up will give us images either in RGB24 format or
        # in Monochrome 8-bit format, depending on the zoom level.
        #
        # This function maps LIMA image mode numbers to PIL image format
        # names, so that we can convert both of the images to a JPEG image.
        #

        if image_mode == IMAGE_MODE_RGB:
            pil_mode = "RGB"
            pixels = frame[header_size:]
        else:
            # should be image in monochrome 8-bit format
            assert image_mode == IMAGE_MODE_L
            pil_mode = "L"

            # the MD3UP tango device sends some extra bytes when in the monochrome mode,
            # we need to cut them off
            end = header_size + (width * height)
            pixels = frame[header_size:end]

        image = Image.frombytes(pil_mode, (width, height), pixels)
        return width, height, image

    def _get_jpg_image(self):
        """
        get one frame from tango device and encode it as jpeg
        """
        try:
            width, height, image = self._get_frame()

            buffer = BytesIO()
            image.save(buffer, "JPEG")

            jpg_img = buffer.getvalue()
            return width, height, jpg_img
        except tango.CommunicationFailed:
            log.warning("failed to fetch video frame from MD3", exc_info=True)
            # show the user the pink 'frame is missing' image,
            # when we can't fetch latest video frame
            return MISSING_FRAME_WIDTH, MISSING_FRAME_WIDTH, self._frame_missing_image

    def _poll(self):
        def fetch_images():
            while self._poll_images:
                width, height, jpg_img = self._get_jpg_image()
                self.emit("imageReceived", jpg_img, width, height)
                time.sleep(self._poll_interval)

        while True:
            self._start_polling.wait()
            self._start_polling.clear()
            fetch_images()

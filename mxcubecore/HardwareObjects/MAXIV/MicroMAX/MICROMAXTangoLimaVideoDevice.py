import struct
import numpy as np
import uuid

from mxcubecore.HardwareObjects.TangoLimaVideoDevice import TangoLimaVideoDevice


class MICROMAXTangoLimaVideoDevice(TangoLimaVideoDevice):
    """Video calss to stream the microscope images"""

    def __init__(self, name):
        TangoLimaVideoDevice.__init__(self, name)

    def init(self):
        super().init()
        self.stream_hash = str(uuid.uuid1())

    def take_snapshot(self, bw=None, return_as_array=True):
        self.get_snapshot(bw, return_as_array)

    def gray_to_rgb(self, width, height, pixels):
        rgb = bytearray(width * height * 3)
        print(len(pixels))
        print(width * height)
        for n in range(width * height):
            v = pixels[n]
            p = n * 3
            rgb[p] = v  ############
            rgb[p + 1] = v
            rgb[p + 2] = v

        return bytes(rgb)

    def get_image(self):
        """
        Reads image from `video_last_image` attribute of lima device proxy,
        which is type of `bytes` and converts it into np.array of int.

        Returns
            raw_buffer : 1d np.array of np.uint16
                Image
            width : int
                Image width
            height : int
                Image height
        """
        img_data = self.device.video_last_image

        if img_data[0] == "VIDEO_IMAGE":
            raw_fmt = img_data[1][: self.header_size]
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
                self.header_fmt, img_data[1][: self.header_size]
            )
            if img_mode == 0:  # GRAY
                raw_buffer = self.gray_to_rgb(
                    width, height, img_data[1][self.header_size :]
                )  # bytes
                raw_buffer = np.frombuffer(raw_buffer, np.uint16)  # array
            else:
                raw_buffer = np.fromstring(
                    img_data[1][self.header_size :], np.uint16
                )  # array

            return raw_buffer, width, height
        else:
            return None, 0, 0

    def get_image_array(self):
        img_data = self.device.video_last_image
        # magic_number, version, image_mode, frame_number, width, height, endianness, header_size = \
        # struct.unpack(">IHHqiiHH", frame[0:28])
        print(img_data)
        if img_data[0] == "VIDEO_IMAGE":
            raw_buffer = np.fromstring(img_data[1][self.header_size :], np.uint8)
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
                self.header_fmt, img_data[1][: self.header_size]
            )
            return raw_buffer, width, height

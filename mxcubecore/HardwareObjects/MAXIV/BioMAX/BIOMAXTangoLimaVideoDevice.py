import struct
import numpy as np
import uuid

from mxcubecore.HardwareObjects.TangoLimaVideoDevice import TangoLimaVideoDevice

class BIOMAXTangoLimaVideoDevice(TangoLimaVideoDevice):
    """Video calss to stream the microscope images"""
    def __init__(self, name):
        TangoLimaVideoDevice.__init__(self, name)
        self.cam_encoding = self.default_cam_encoding
    
    def init(self):
        super().init()
        self.stream_hash = str(uuid.uuid1())

    def set_cam_encoding(self, cam_encoding):
        if cam_encoding == "yuv422p":
            self.decoder = self.yuv_2_rgb
        elif cam_encoding == "y8":
            self.decoder = self.y8_2_rgb
        elif cam_encoding == "y16":
            self.decoder = self.y16_2_rgb
        elif cam_encoding == "bayer_rg16":
            self.decoder = self.bayer_rg16_2_rgb
        self.cam_encoding = cam_encoding


    def take_snapshot(self, bw=None, return_as_array=True):
        self.get_snapshot(bw, return_as_array)

    def get_image_array(self):
        img_data = self.device.video_last_image

        if img_data[0]=="VIDEO_IMAGE":
            raw_buffer = np.fromstring(img_data[1][self.header_size:], np.uint8)
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(self.header_fmt, img_data[1][:self.header_size])
            return  raw_buffer, width, height


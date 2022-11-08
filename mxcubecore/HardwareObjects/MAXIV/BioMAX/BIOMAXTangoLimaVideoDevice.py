import struct
import numpy as np
import uuid

from mxcubecore.HardwareObjects.TangoLimaVideoDevice import TangoLimaVideoDevice

class BIOMAXTangoLimaVideoDevice(TangoLimaVideoDevice):
    """Video calss to stream the microscope images"""
    def __init__(self, name):
        TangoLimaVideoDevice.__init__(self, name)
    
    def init(self):
        super().init()
        self.stream_hash = str(uuid.uuid1())

    def get_image_array(self):
        img_data = self.device.video_last_image

        if img_data[0]=="VIDEO_IMAGE":
            raw_buffer = np.fromstring(img_data[1][self.header_size:], np.uint8)
            _, ver, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(self.header_fmt, img_data[1][:self.header_size])
            return  raw_buffer, width, height


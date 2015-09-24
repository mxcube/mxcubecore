import logging
from HardwareRepository import HardwareRepository
import BeamInfo

class ID30A3BeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self): 
        BeamInfo.BeamInfo.init(self)
 
        self.beam_size_slits = [0.015, 0.015]
        self.camera = self.getDeviceByRole("camera")
        self.beam_position = (self.camera.getWidth() / 2, self.camera.getHeight() / 2)

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self,*args):
        BeamInfo.BeamInfo.evaluate_beam_info(self,*args)
        self.beam_info_dict["shape"] = "ellipse"
        return self.beam_info_dict
     

import logging
from HardwareRepository import HardwareRepository
import BeamInfo

class MAXLABBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self): 
        self.chan_beam_size_microns = None 
        self.chan_beam_shape_ellipse = None 
        BeamInfo.BeamInfo.init(self)
        
        self.camera = self.getDeviceByRole('camera')
        self.get_beam_position()
        self.get_beam_size()
#        self.beam_size_aperture=self.aperture_hwobj.getApertureSize()
        self.aperture_pos_changed(self.aperture_hwobj.getApertureSize())
        self.emit("beamInfoChanged", (self.beam_info_dict, ))
        self.emit("beamPosChanged", (self.beam_position, ))

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        logging.info ("camera is %s", str(self.camera))
        if self.camera is not None:
            self.beam_position[0] = self.camera.getWidth() / 2
            self.beam_position[1] = self.camera.getHeight() / 2
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self,*args):
        BeamInfo.BeamInfo.evaluate_beam_info(self,*args)
        self.beam_info_dict["shape"] = "circular"#"ellipse"
        curpos=self.aperture_hwobj.getCurrentPositionName()
        size_x = size_y = eval(str(curpos)) / 1000.0
        self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y
        return self.beam_info_dict

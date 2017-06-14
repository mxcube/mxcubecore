"""
[Name] BeamInfo

[Description]
BeamInfo hardware object is used to define final beam size and shape.
It can include aperture, slits and/or other beam definer (lenses or other eq.)

[Emited signals]
beamInfoChanged

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
 aperture_hwobj	    apertureChanged
 slits_hwobj
 beam_definer_hwobj
-----------------------------------------------------------------------
"""

import logging
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Equipment

class BeamInfoMockup(Equipment):

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.beam_size_slits = [9999, 9999]
        self.beam_size_aperture = [0.01, 0.01]
        self.beam_size_definer = [9999, 9999]
        self.beam_position = [300, 300]
        self.beam_info_dict = {}

    def init(self):
        self.aperture_hwobj = self.getObjectByRole("aperture")
        self.emit("beamPositionChanged", (self.beam_position, ))

    def get_beam_position(self):
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        self.beam_position = [beam_x, beam_y]
        self.emit("beamPositionChanged", (self.beam_position, ))

    def get_beam_info(self):
        return self.evaluate_beam_info()
 
    def get_beam_size(self):
        """
        Description: returns beam size in microns
        Returns: list with two integers
        """
        self.evaluate_beam_info()
        return float(self.beam_info_dict["size_x"]), \
               float(self.beam_info_dict["size_y"])

    def get_beam_shape(self):
        self.evaluate_beam_info()
        return self.beam_info_dict["shape"]

    def get_slits_gap(self):
        self.evaluate_beam_info()
        return self.beam_size_slits	

    def evaluate_beam_info(self):
        """
        Description: called if aperture, slits or focusing has been changed
        Returns: dictionary, {size_x: 0.1, size_y: 0.1, shape: "rectangular"}
        """
        size_x = min(self.beam_size_aperture[0],
                     self.beam_size_slits[0],
                     self.beam_size_definer[0]) 
        size_y = min(self.beam_size_aperture[1],
                     self.beam_size_slits[1], 
                     self.beam_size_definer[1]) 
	
        self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y

        if tuple(self.beam_size_aperture) < tuple(self.beam_size_slits):
            self.beam_info_dict["shape"] = "ellipse"
        else:
            self.beam_info_dict["shape"] = "rectangular"
        return self.beam_info_dict	

    def emit_beam_info_change(self): 
        if self.beam_info_dict["size_x"] != 9999 and \
            self.beam_info_dict["size_y"] != 9999:		
            self.emit("beamSizeChanged", ((self.beam_info_dict["size_x"],\
                      self.beam_info_dict["size_y"]), ))
            self.emit("beamInfoChanged", (self.beam_info_dict, ))

    def get_beam_divergence_hor(self):
        return 0

    def get_beam_divergence_ver(self):
        return 0

    def get_aperture_pos_name(self):
        if self.aperture_hwobj:
            return self.aperture_hwobj.get_current_pos_name()

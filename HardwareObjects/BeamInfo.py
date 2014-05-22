"""
[Name] BeamInfo

[Description]

[Channels]

[Commands]

[Emited signals]

[Functions]

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
 apertureHO
 slitsHO
 focusingHO
-----------------------------------------------------------------------
"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment


class BeamInfo(Equipment):

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.beam_size_slits = [float("inf"), float("inf")]
        self.beam_size_aperture = [float("inf"), float("inf")]
        self.beam_size_focusing = [float("inf"), float("inf")]
        self.apertureHO = None
        self.slitsHO = None
        self.focusingHO = None
        
        self.beam_info_dict = {}

    def init(self):

        self.apertureHO = self.getDeviceByRole("aperture")
        self.slitsHO = self.getDeviceByRole("slits")
        self.focusingHO = self.getDeviceByRole("focusing")

        if self.apertureHO is not None:
           self.connect(self.apertureHO, "predefinedPositionChanged", self.aperture_pos_changed)
        else:
           logging.getLogger("HWR").debug('BeamInfo: aperture not defined')
        if self.slitsHO is not None:
           self.connect(self.slitsHO, "gapSizeChanged", self.slits_gap_changed)
        else:
           logging.getLogger("HWR").debug('BeamInfo: slits not defined')
        if self.focusingHO:
           self.connect(self.focusingHO, "focusModeChanged", self.focusing_changed)
        else:
           logging.getLogger("HWR").debug('BeamInfo: focusing not defined')

        self.chan_beam_size_hor = self.getChannelObject("beam_size_hor")
        self.chan_beam_size_ver = self.getChannelObject("beam_size_ver")
        self.chan_beam_ellipse  = self.getChannelObject("beam_size_ellipse")

    def aperture_pos_changed(self, size):
        self.beam_size_aperture = size
        self.evaluate_beam_info() 

    def slits_gap_changed(self, size):
        self.beam_size_slits = size
        self.evaluate_beam_info()

    def focusing_changed(self, size):
        self.beam_size_focusing = size
        self.evaluate_beam_info()

    def get_beam_info(self):
        return self.evaluate_beam_info()
        
    def get_beam_size(self):
        return self.beam_info_dict["size_x"], self.beam_info_dict["size_y"]

    def get_beam_shape(self):
        return self.beam_info_dict["shape"]

    def evaluate_beam_info(self):
        """
        Description: called if aperture, slits or focusing has been changed
        Returns: dictionary, for example {size_x: 0.1, size_y: 0.1, shape: "rectangular"}
        """
	    if self.focusingHO is not None:
            self.beam_info_dict["size_x"] = self.beam_size_focusing[0]
            self.beam_info_dict["size_y"] = self.beam_size_focusing[1]
	    else:
            self.beam_info_dict["size_x"] = min (self.beam_size_slits[0], self.beam_size_aperture[0])
            self.beam_info_dict["size_y"] = min (self.beam_size_slits[1], self.beam_size_aperture[1])
        if (self.beam_size_aperture < self.beam_size_slits):
	        self.beam_info_dict["shape"] = "ellipse"
	    else:
	        self.beam_info_dict["shape"] = "rectangular"
	
	    self.emit("beamInfoChanged", (self.beam_info_dict, ))
		
        if self.chan_beam_size_hor is not None:
            self.chan_beam_size_hor.setValue(self.beam_info_dict["size_x"])
        if self.chan_beam_size_ver is not None:
            self.chan_beam_size_ver.setValue(self.beam_info_dict["size_y"])
        if self.chan_beam_size_ellipse is not None:
            self.chan_beam_size_ellipse.setValue(self.beam_info_dict["shape"] == "ellipse")

        return self.beam_info_dict

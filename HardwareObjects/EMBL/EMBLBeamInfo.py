#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] EMBLBeamInfo

[Description]
Hardware object is used to define final beam size and shape.
It can include aperture, slits and/or beam focusing hwobj

[Emited signals]
beamInfoChanged

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals          | functions
-----------------------------------------------------------------------
 aperture_hwobj	    apertureChanged
 slits_hwobj	    	
 beam_focusing_hwobj
-----------------------------------------------------------------------
"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment


__author__ = "Ivars Karpics"
__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLBeamInfo(Equipment):
    """
    Description:
    """  	

    def __init__(self, *args):
        """
        Descrip. :
        """
        Equipment.__init__(self, *args)

        self.aperture_hwobj = None
        self.slits_hwobj = None
        self.beam_focusing_hwobj = None

        self.beam_size_slits = None
        self.beam_size_aperture = None
        self.beam_size_focusing = None
        self.beam_position = None
        self.beam_info_dict = None
        self.aperture_pos_name = None
        self.default_beam_divergence = None

        self.chan_beam_position_hor = None
        self.chan_beam_position_ver = None
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None

    def init(self):
        """
        Descript. : 
        """
        self.beam_size_slits = [9999, 9999]
        self.beam_size_aperture = [9999, 9999]
        self.beam_size_focusing = [9999, 9999]
        self.beam_position = [0, 0]
        self.beam_info_dict = {"size_x" : 0,
                               "size_y" : 0}

        self.aperture_hwobj = self.getObjectByRole("aperture")
        if self.aperture_hwobj is not None:
            self.connect(self.aperture_hwobj, 
                         "diameterIndexChanged",
                         self.aperture_diameter_changed)
        else:
            logging.getLogger("HWR").debug("BeamInfo: Aperture hwobj not defined") 

        self.slits_hwobj = self.getObjectByRole("slits")
        if self.slits_hwobj is not None:  
            self.connect(self.slits_hwobj, 
                         "gapSizeChanged",
                         self.slits_gap_changed)
        else:
            logging.getLogger("HWR").debug("BeamInfo: Slits hwobj not defined")

        self.beam_focusing_hwobj = self.getObjectByRole("beam_focusing")
        if self.beam_focusing_hwobj is not None:
            focus_mode_name, self.beam_size_focusing = \
                  self.beam_focusing_hwobj.get_active_focus_mode()
            self.connect(self.beam_focusing_hwobj, 
                         "focusingModeChanged", \
                         self.focusing_mode_changed)
        else:
            logging.getLogger("HWR").debug("BeamInfo: Beam focusing hwobj not defined")

        self.chan_beam_position_hor = self.getChannelObject("BeamPositionHorizontal")
        if self.chan_beam_position_hor:
            self.chan_beam_position_hor.connectSignal("update", self.beam_pos_hor_changed)
        self.chan_beam_position_ver = self.getChannelObject("BeamPositionVertical")
        if self.chan_beam_position_ver:
            self.chan_beam_position_ver.connectSignal("update", self.beam_pos_ver_changed)
        self.chan_beam_size_microns = self.getChannelObject("BeamSizeMicrons")
        self.chan_beam_shape_ellipse = self.getChannelObject("BeamShapeEllipse")
        self.default_beam_divergence = eval(self.getProperty("defaultBeamDivergence"))
 
    def get_beam_divergence_hor(self):
        """
        Descript. : 
        """
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_divergence_hor() 
        else:
            return self.default_beam_divergence[0]
    
    def get_beam_divergence_ver(self):
        """
        Descript. : 
        """
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_divergence_ver()
        else:
            return self.default_beam_divergence[1]
 
    def beam_pos_hor_changed(self, value):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position[0] = value
        self.emit("beamPosChanged", (self.beam_position, ))

    def beam_pos_ver_changed(self, value):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position[1] = value 
        self.emit("beamPosChanged", (self.beam_position, ))

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        if self.chan_beam_position_hor and self.chan_beam_position_ver:
            self.beam_position = [self.chan_beam_position_hor.getValue(), \
	                          self.chan_beam_position_ver.getValue()]
        return self.beam_position	

    def set_beam_position(self, beam_x, beam_y):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position = [beam_x, beam_y]
        
        if self.chan_beam_position_hor and self.chan_beam_position_ver:
            self.chan_beam_position_hor.setValue(int(beam_x))
            self.chan_beam_position_ver.setValue(int(beam_y))
        else:
            #Act like mockup
            self.emit("beamPosChanged", (self.beam_position, ))

    def aperture_diameter_changed(self, name, size):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_size_aperture = [size, size]
        self.aperture_pos_name = name
        self.evaluate_beam_info() 
        self.emit_beam_info_change()

    def get_aperture_pos_name(self):
        if self.aperture_hwobj:
            return self.aperture_hwobj.get_current_pos_name()

    def slits_gap_changed(self, size):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_size_slits = size
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def focusing_mode_changed(self, name, size):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_size_focusing = size
        self.evaluate_beam_info()
        self.emit_beam_info_change()

    def get_beam_info(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        return self.evaluate_beam_info()
        
    def get_beam_size(self):
        """
        Descript. : returns beam size in microns
        Return   : list with two integers
        """
        self.evaluate_beam_info()
        return (self.beam_info_dict["size_x"], \
	        self.beam_info_dict["size_y"])

    def get_beam_shape(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.evaluate_beam_info()
        return self.beam_info_dict["shape"]

    def get_slits_gap(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.evaluate_beam_info()
        if self.beam_size_slits == [9999, 9999]:
            return [None, None]
        else: 
            return self.beam_size_slits	

    def set_slits_gap(self, width_microns, height_microns):
        if self.slits_hwobj:
            self.slits_hwobj.set_gap("Hor", width_microns / 1000.0)
            self.slits_hwobj.set_gap("Ver", height_microns / 1000.0)        

    def evaluate_beam_info(self):
        """
        Descript. : called if aperture, slits or focusing has been changed
        Return    : dictionary,{size_x:0.1, size_y:0.1, shape:"rectangular"}
        """
        size_x = min(self.beam_size_aperture[0],
	   	     self.beam_size_slits[0],
		     self.beam_size_focusing[0]) 
        size_y = min(self.beam_size_aperture[1],
  		     self.beam_size_slits[1], 
		     self.beam_size_focusing[1]) 

        if size_x == 9999 or size_y == 999:
            #fix this
            return
        if (abs(size_x - self.beam_info_dict.get("size_x", 0)) > 1e-3 or
            abs(size_y - self.beam_info_dict.get("size_y", 0)) > 1e-3):	
            self.beam_info_dict["size_x"] = size_x
            self.beam_info_dict["size_y"] = size_y

            if self.beam_size_aperture <= [size_x, size_y]:
                self.beam_info_dict["shape"] = "ellipse"
            else:
                self.beam_info_dict["shape"] = "rectangular"
            
            if self.chan_beam_size_microns is not None:
                self.chan_beam_size_microns.setValue((self.beam_info_dict["size_x"] * 1000, \
                     self.beam_info_dict["size_y"] * 1000))
            if self.chan_beam_shape_ellipse:
                self.chan_beam_shape_ellipse.setValue(self.beam_info_dict["shape"] == "ellipse")

        return self.beam_info_dict	

    def emit_beam_info_change(self): 
        """
        Descript. :
        Arguments :
        Return    :
        """
        if (self.beam_info_dict["size_x"] != 9999 and \
            self.beam_info_dict["size_y"] != 9999):		
            self.emit("beamSizeChanged", ((self.beam_info_dict["size_x"] * 1000, \
                                           self.beam_info_dict["size_y"] * 1000), ))
            self.emit("beamInfoChanged", (self.beam_info_dict, ))

    def get_beam_info(self):
        self.evaluate_beam_info()
        return self.beam_info_dict

    def update_values(self):
        self.emit("beamInfoChanged", (self.beam_info_dict, ))
        self.emit("beamPosChanged", (self.beam_position, ))

    def move_beam(self, direction, step):
        if direction == 'left':
            self.chan_beam_position_hor.setValue(self.beam_position[0] - 1)
        elif direction == 'right':
            self.chan_beam_position_hor.setValue(self.beam_position[0] + 1)
        elif direction == 'up':
            self.chan_beam_position_ver.setValue(self.beam_position[1] - 1)
        elif direction == 'down':
            self.chan_beam_position_ver.setValue(self.beam_position[1] + 1) 

    def get_focus_mode(self):
        if self.beam_focusing_hwobj is not None:
            return self.beam_focusing_hwobj.get_focus_mode()        

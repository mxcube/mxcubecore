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
[Name] EMBLAperture

[Description]
Hardware Object is used to set and get current aperture.

[Channels]

[Commands]

[Emited signals]
- apertureChanged

[Functions]
- setAllowedPositions()
- getShape()
- activePosChanged()
- setActivePos()
- isPosAllowed()
- focModeChanged()
- evaluateAperture()
 
[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals        | functions
-----------------------------------------------------------------------
| BeamFocusing    | focModeChanged |
-----------------------------------------------------------------------

Example Hardware Object XML file :
==================================
"""

import logging
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class EMBLAperture(Device):
    """
    Description:	
    """	
    POSITIONS = ("BEAM", "OFF", "PARK")

    def __init__(self, name):
        """
        Description: Active position is defined as index (int)	
        """
        Device.__init__(self, name)

        self.position = None
        self.current_diameter_index = None
        self.diameter_list = []

        self.chan_diameter_index = None
        self.chan_diameters = None
        self.chan_position = None
  
    def init(self):
        """
	Description:
	"""

        self.chan_diameters = self.getChannelObject('ApertureDiameters')
        if self.chan_diameters:
            self.diameter_list = self.chan_diameters.getValue()         
        else:
            self.diameter_list = [10, 20]

        self.chan_diameter_index = self.getChannelObject('CurrentApertureDiameterIndex')
        if self.chan_diameter_index is not None: 
            self.current_diameter_index = self.chan_diameter_index.getValue()
            self.diameter_index_changed(self.current_diameter_index)
            self.chan_diameter_index.connectSignal('update', self.diameter_index_changed)
        else:
            self.current_diameter_index = 0
        
        self.chan_position = self.getChannelObject('AperturePosition')
        if self.chan_position:
            self.position = self.chan_position.getValue()
            self.position_changed(self.position) 
            self.chan_position.connectSignal('update', self.position_changed)

    def diameter_index_changed(self, diameter_index):
        """
        Descript. :
        """
        self.current_diameter_index = diameter_index
        self.emit('diameterIndexChanged', diameter_index, 
             self.diameter_list[diameter_index] / 1000.0)

    def get_diameter_size(self):
        return self.diameter_list[self.current_diameter_index] / 1000.0

    def position_changed(self, position):
        self.position = position
        self.emit('positionChanged', position)

    def set_diameter_index(self, diameter_index):
        """   
        Description : cmd to set new aperture
        Arguments   : new aperture name(string) 
        Return      : -
        """
        self.chan_diameter_index.setValue(diameter_index)

    def set_diameter(self, diameter):
        self.chan_diameter_index.setValue(self.diameter_list.index(diameter)) 

    def set_position(self, position):
        self.chan_position.setValue(EMBLAperture.POSITION[position])

    def set_in(self):
        self.chan_position.setValue("BEAM")

    def set_out(self):
        self.chan_position.setValue("OFF")

    def is_out(self):
        return self.position != "BEAM"
	   	
    def get_diameter_list(self):
        """
        Descript. :
        """
        return self.diameter_list

    def get_position_list(self):
        return EMBLAperture.POSITIONS 

    def update_values(self):
        """
        Descript. :
        """
        self.diameter_index_changed(self.current_diameter_index) 
        self.position_changed(self.position)

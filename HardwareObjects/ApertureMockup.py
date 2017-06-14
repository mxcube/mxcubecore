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
"""

import logging
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class ApertureMockup(Device):
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

    def init(self):
        """
	Description:
	"""

        self.diameter_list = [5, 10, 20, 30, 50, 100]
        self.current_diameter_index = 2
        self.diameter_index_changed(self.current_diameter_index)
        self.position = "BEAM"
        self.position_changed(self.position) 

    def get_diameter_size(self):
        return self.diameter_list[self.current_diameter_index] / 1000.0

    def position_changed(self, position):
        self.position = position
        self.emit('positionChanged', position)

    def set_diameter_index(self, diameter_index):
        self.current_diameter_index = diameter_index
        self.diameter_index_changed(self.current_diameter_index)

    def set_diameter(self, diameter):
        self.chan_diameter_index.setValue(self.diameter_list.index(diameter)) 

    def set_position(self, position):
        self.position = position
        self.emit('positionChanged', position)

    def set_in(self):
        self.position = "BEAM"
        self.emit('positionChanged', position)

    def set_out(self):
        self.position = "OFF"
        self.emit('positionChanged', position)

    def is_out(self):
        return self.position != "BEAM"
	   	
    def get_diameter_list(self):
        return self.diameter_list

    def get_position_list(self):
        return ApertureMockup.POSITIONS 

    def update_values(self):
        self.diameter_index_changed(self.current_diameter_index) 
        self.position_changed(self.position)

    def diameter_index_changed(self, diameter_index):
        """
        Descript. :
        """
        self.current_diameter_index = diameter_index
        self.emit('diameterIndexChanged', diameter_index,
             self.diameter_list[diameter_index] / 1000.0)

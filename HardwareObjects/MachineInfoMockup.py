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

import logging
import time
from datetime import datetime, timedelta
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class MachineInfoMockup(HardwareObject):
    """
    Descript. : Displays actual information about the beeamline
    """

    def __init__(self, name):
	HardwareObject.__init__(self, name)
        """
        Descript. : 
        """
        #Parameters
	#Intensity current ranges
        self.values_list = []
        temp_dict = {}
        temp_dict['value'] = 100.1
        temp_dict['in_range'] = True
        temp_dict['title'] = "Machine current"
        temp_dict['bold'] = True
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = "Test message"
        temp_dict['in_range'] = True
        temp_dict['title'] = "Machine state"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 24.4
        temp_dict['in_range'] = True
        temp_dict['title'] = "Hutch temperature"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 64.4
        temp_dict['in_range'] = True
        temp_dict['title'] = "Hutch humidity"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 4e11
        temp_dict['in_range'] = None
        temp_dict['title'] = "Flux"
        self.values_list.append(temp_dict)

    def init(self):
        """
        Descript.
        """
        self.update_values()

    def update_values(self):
        """
        Descript. : Updates storage disc information, detects if intensity
		    and storage space is in limits, forms a value list 
		    and value in range list, both emited by qt as lists
        Arguments : -
        Return    : -
        """
        self.emit('valuesChanged', self.values_list)

    def get_current(self):
        return self.values_list[0]['value']
 
    def get_current_value(self):
        """
        Descript. :
        """     
        return self.values_list[0]['value']

    def	get_message(self):
        """
        Descript :
        """  
        return self.values_list[1]['value']

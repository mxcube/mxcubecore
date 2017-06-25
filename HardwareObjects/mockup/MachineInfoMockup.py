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

import time
from gevent import spawn
from random import uniform

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
        temp_dict['value'] = 90.1
        temp_dict['value_str'] = "90.1 mA"
        temp_dict['in_range'] = True
        temp_dict['title'] = "Machine current"
        temp_dict['bold'] = True
        temp_dict['font'] = 14
        temp_dict['history'] = True
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = "Test message"
        temp_dict['in_range'] = True
        temp_dict['title'] = "Machine state"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 24.4
        temp_dict['value_str'] = "24.4 C"
        temp_dict['in_range'] = True
        temp_dict['title'] = "Hutch temperature"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 64.4
        temp_dict['value_str'] = "64.4 %"
        temp_dict['in_range'] = True
        temp_dict['title'] = "Hutch humidity"
        self.values_list.append(temp_dict)

        temp_dict = {}
        temp_dict['value'] = 4e11
        temp_dict['value_str'] = "4e+11 ph/s"
        temp_dict['in_range'] = False
        temp_dict['title'] = "Flux"
        self.values_list.append(temp_dict)

    def init(self):
        """
        Descript.
        """
        self.update_values()
        spawn(self.change_mach_current)
       
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

    def change_mach_current(self):
        while True:
            self.values_list[0]['value'] = uniform(80.1, 90.1)
            self.values_list[0]['value_str'] = "%.1f mA" % \
                 self.values_list[0]['value']
            self.update_values()
            time.sleep(5)

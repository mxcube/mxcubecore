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
from time import sleep
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class SlitsMockup(HardwareObject):

    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self.hor_gap = False
        self.ver_gap = False
	
    def init(self):
        self.gaps_dict = {}
        self.gaps_dict['Hor'] = self['gapH'].getProperties()
        self.gaps_dict['Ver'] = self['gapV'].getProperties()
        self.gaps_dict['Hor']['value'] = 0.10
        self.gaps_dict['Ver']['value'] = 0.10
        self.gaps_dict['Hor']['status'] = ''
        self.gaps_dict['Ver']['status'] = ''
        self.init_max_gaps = self.get_max_gaps()
        self.emit('statusChanged', "Ready", "Ready")

    def get_step_sizes(self):
        """
        Descript. : returns Hor and Ver step sizes
        Arguments : -                                        
        Return    : step size values (list of two values)
        """
        return [self.gaps_dict['Hor']['stepSize'], 
                self.gaps_dict['Ver']['stepSize']]

    def get_min_gaps(self):
        """
        Descript. : returns min Hor and Ver gaps values
        Arguments : -                                        
        Return    : min gap values (list of two values)
        """
        return [self.gaps_dict['Hor']['minGap'], 
                self.gaps_dict['Ver']['minGap']]		

    def get_max_gaps(self):
        """
        Descript. : returns max Hor and Ver gaps values
        Arguments : -                                        
        Return    : max gap values (list of two values)
	"""
        return [self.gaps_dict['Hor']['maxGap'], 
                self.gaps_dict['Ver']['maxGap']] 	

    def get_gap_limits(self, gap_name):
        """
        Descript. : returns gap min and max limits
        Arguments : gap name                                        
        Return    : min and max gap values (list of two values)
        """
        return [self.gaps_dict[gap_name]['minGap'],
                self.gaps_dict[gap_name]['maxGap']]           

    def get_gap_hor(self):
        """
        Descript. : evaluates Horizontal gap
        Arguments : -                                        
        Return    : Hor gap value in mm 
        """
        return self.gaps_dict['Hor']['value']

    def get_gap_ver(self):
        """
        Descript. : evaluates Vertical gap
        Arguments : -                                        
        Return    : Ver gap value in mm
        """
        return self.gaps_dict['Ver']['value']
   
    def get_gaps(self):
        """
        Descript.
        """
        return self.get_gap_hor(), self.get_gap_ver()
	
    def set_gap(self, gap_name, new_gap):
        """Sets new gap value
        Arguments : gap name(string), gap value(float)                                        
        """
        self.emit('statusChanged', ("Move", "Move"))
        sleep(1)
        self.gaps_dict[gap_name]['value'] = new_gap
        self.emit('gapSizeChanged', [self.gaps_dict['Hor']['value'],
                self.gaps_dict['Ver']['value']])
        self.emit('statusChanged', ("Ready", "Ready"))

    def stop_gap_move(self, gap_name):
        """
        Descript.: stops motors movements
        Arguments: gap name(string)                                        
        """
        return

    def set_gaps_limits(self, new_gaps_limits):
        """
        Descript. : sets max gap Limits
        Arguments : [max Hor gap, max Ver gap (list of two float values)                                        
        Return    : -
        """
        if new_gaps_limits is not None:
            self.gaps_dict['Hor']['maxGap'] = min(self.init_max_gaps[0], new_gaps_limits[0])
            self.gaps_dict['Ver']['maxGap'] = min(self.init_max_gaps[1], new_gaps_limits[1])	
            self.emit('gapLimitsChanged', [self.gaps_dict['Hor']['maxGap'], 
                                           self.gaps_dict['Ver']['maxGap']])

    def update_values(self):
        """
        Descript. :
        """
        self.emit('gapSizeChanged', [self.gaps_dict['Hor']['value'],
                                     self.gaps_dict['Ver']['value']])
        self.emit('statusChanged', ("Ready", "Ready"))
        self.emit('focusModeChanged', (True, True))

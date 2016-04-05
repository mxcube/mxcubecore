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
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLAperture(Device):
    """
    Description:	
    """	
    def __init__(self, name):
        """
        Description: Active position is defined as index (int)	
        """
        Device.__init__(self, name)

        self.active_position = None
        self.default_position = None
        self.positions_list = []
        self.active_focus_mode = None    

        self.chan_current_aperture_diameter_index = None
        self.chan_aperture_position = None
  
        self.beam_focusing_hwobj = None

    def init(self):
        """
	Description:
	"""
        for position in self['positions']:
            temp_name = str(position.getProperty('posName'))
            if not temp_name == "Out":
                temp_name = "%s%sm" % (temp_name, unichr(956))
            self.positions_list.append({
                 'origin_name' : str(position.getProperty('posName')),
                 'name'   : temp_name,
                 'modes'  : position.getProperty('modesAllowed'),
                 'size'   : eval(position.getProperty('size'))})
        self.default_position = self.getProperty('defaultPosition')
        self.chan_current_aperture_diameter_index = \
             self.getChannelObject('CurrentApertureDiameterIndex')
        if self.chan_current_aperture_diameter_index is not None: 
            self.chan_current_aperture_diameter_index.\
                 connectSignal('update', self.active_position_changed)
            self.active_position_changed(\
                 self.chan_current_aperture_diameter_index.getValue())

        self.chan_aperture_position = self.getChannelObject('AperturePosition')

        self.beam_focusing_hwobj = self.getObjectByRole('beam_focusing')
        if self.beam_focusing_hwobj:
            self.connect(self.beam_focusing_hwobj, 
                         'focusingModeChanged', 
                         self.beam_focus_changed)

        self.active_position = 0
        self.active_focus_mode = "Unfocused"
        self.evaluate_aperture()

    def active_position_changed(self, new_position):
        """
        Descript. :
        """
        if new_position is not None:
            self.active_position = int(new_position)
            self.evaluate_aperture()

    def update_values(self):
        """
        Descript. :
        """
        if self.chan_current_aperture_diameter_index is not None:
            self.active_position = self.chan_current_aperture_diameter_index.getValue()
        #if self.beam_focusing_hwobj is not None:
        #    self.active_focus_mode =  
        self.active_position_changed(self.active_position) 
	
    def set_active_position(self, new_position):
        """   
        Description : cmd to set new aperture
        Arguments   : new aperture name(string) 
        Return      : -
        """
        if new_position == 'def':
            new_position = self.default_position
        if self.active_focus_mode is not None:
            if self.active_focus_mode in self.positions_list[new_position]['modes'] \
            and self.chan_current_aperture_diameter_index:
                self.chan_current_aperture_diameter_index.setValue(new_position)	
            else:
                 #Mockup 
                self.active_position_changed(new_position)
        else:
            if self.chan_current_aperture_diameter_index:
                self.chan_current_aperture_diameter_index.setValue(new_position)
            else:
                #Mockup
                self.active_position_changed(new_position) 
	   	
    def focus_mode_changed(self, new_focus_mode, size):
        """
        Description : called by focusing mode change. Changes focusing
                      mode and updates aperture info
        Arguments   : new focus mode (string)      
        Return      : -
	"""
        if self.active_focus_mode != new_focus_mode:
            self.active_focus_mode  = new_focus_mode
            self.evaluate_aperture()

    def get_value(self):
        """
        Descript. :     
        Arguments :
        Return    :
        """
        return self.active_position

    def get_current_pos_name(self):
        """
        Descript. :
        """
        return self.positions_list[self.active_position]['origin_name'] 

    def get_aperture_list(self, as_origin=None):
        """
        Descript. :
        """
        position_names = []
        if len(self.positions_list) > 0:
            for position in self.positions_list:
                if as_origin:
                    position_names.append(position['origin_name'])
                else:
                    position_names.append(position['name'])
        return position_names        

    def set_in(self):
        """
        Descript. :
        """
        self.chan_aperture_position.setValue('BEAM')

    def set_out(self):
        """
        Descript. :
        """
        self.chan_aperture_position.setValue('OFF')

    def evaluate_aperture(self):	
        """
        Descript. : evaluates aperture position. If aper not allowed sets to default
        Arguments : - 
        Return    : -
        """
        if self.beam_focusing_hwobj is None:
            self.emit('apertureChanged', (self.active_position, 
                      self.positions_list[self.active_position]['size']))
        else:
            """if self.active_position is not None:
                if not self.getPosFromName(self.activePos)['allowed']:
                    self.setActivePos('def')
                    logging.getLogger("HWR").info('BeamAperture: aperture set\
                            to default due to beam focus') 	"""
            if (self.active_focus_mode is None or 
                self.active_position is None):
                self.emit('apertureChanged', (None, [0, 0]))
            else:
                self.emit('apertureChanged', (self.active_position, 
                     self.positions_list[self.active_position]['size']))

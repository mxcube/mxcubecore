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
[Name] EMBLBeamFocusing

[Description]
Hardware Object is used to evaluate and set beam focusing mode.

[Channels]

[Commands]

[Emited signals]
- focusModeChanged 

[Functions]
- mGroupFocModeChanged()
- getFocModesNames()
- getFocMode()
- setFocMode()

[Included Hardware Objects]
-----------------------------------------------------------------------
| name            | signals              | functions
-----------------------------------------------------------------------
| MotorsGroup     | mGroupFocModeChanged | setMotorGroupFocMode()
-----------------------------------------------------------------------

Example Hardware Object XML file :
==================================
<equipment class="BeamFocusing">
    <focusModes>
      <focusMode>
           <modeName>Unfocused</modeName>
           <message>'Set beam focusing to Unfocused mode'</message>
      </focusMode>
</equipment>
"""

import logging
from _tine import query as tinequery
from HardwareRepository.BaseHardwareObjects import Equipment


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLBeamFocusing(Equipment):
    """
    Descript. :
    """
    def __init__(self, name):
        """
        Descript. :
        """
        Equipment.__init__(self, name) 
        self.active_focus_mode = None
        self.size = [9999, 9999]
        self.focus_modes = None
        self.focus_motors_dict = None
        self.motors_groups = []

        self.cmd_set_calibration_name = None
        self.cmd_set_phase = None 

    def init(self):
        """
        Descript. :
        """
        self.focus_modes = [] 
        for focus_mode in self['focusModes']:
            self.focus_modes.append({'modeName': focus_mode.modeName, 
                                     'lensCombination': eval(focus_mode.lensCombination),
                                     'lensModes': eval(focus_mode.lensModes),
                                     'size': eval(focus_mode.size), 
                                     'message': eval(focus_mode.message),
                                     'diverg': eval(focus_mode.divergence)})
        self.focus_motors_dict = {} 

        focus_motors = []
        try: 
            focus_motors = eval(self.getProperty('focusMotors'))
        except:
            pass
      
        for focus_motor in focus_motors:
            self.focus_motors_dict[focus_motor] = []
       
        self.motors_groups = self.getDevices()
        if len(self.motors_groups) > 0:
            for motors_group in self.motors_groups:
                self.connect(motors_group, 'mGroupFocModeChanged', 
                     self.motor_group_focus_mode_changed)
        else:
            logging.getLogger("HWR").debug('BeamFocusing: No motors defined') 
            self.active_focus_mode = self.focus_modes[0]['modeName'] 
            self.size = self.focus_modes[0]['size']
            self.update_values()
        
        self.cmd_set_calibration_name = self.getCommandObject(\
            'cmdSetCallibrationName')
        try:
            self.cmd_set_phase = eval(self.getProperty('setPhaseCmd'))
        except:
            pass 

    def get_focus_motors(self):
        """
        Descript. :
        """ 
        focus_motors = []
        if self.motors_groups is not None:
            for motors_group in self.motors_groups:
                motors_group_list = motors_group.get_motors_dict()
                for motor in motors_group_list:
                    focus_motors.append(motor)
        return focus_motors

    def motor_group_focus_mode_changed(self, value):
        """
	Descript. : called if motors group focusing is changed 
        Arguments : new focus mode name(string                                 
        Return    : -
        """
        motors_group_foc_mode = eval(value)
        for motor in motors_group_foc_mode:
            if motor in self.focus_motors_dict:
                self.focus_motors_dict[motor] = motors_group_foc_mode[motor]

        prev_mode = self.active_focus_mode
        self.active_focus_mode, self.size = self.get_active_focus_mode()

        if prev_mode != self.active_focus_mode:
            logging.getLogger("HWR").info('Focusing: %s mode detected' % self.active_focus_mode)
            self.emit('focusingModeChanged', self.active_focus_mode, self.size)
            if self.cmd_set_calibration_name and self.active_focus_mode:
                self.cmd_set_calibration_name(self.active_focus_mode.lower())

    def get_focus_mode_names(self):
        """
        Descript. : returns defined focus modes names 
        Arguments : -                                        
        Return    : focus mode names (list of strings)
        """
        names = []
        for focus_mode in self.focus_modes:
            names.append(focus_mode['modeName'])
        return names

    def get_focus_mode_message(self, focus_mode_name):
        """
        Descript. : returns foc mode message
        Arguments : mode name (string)                                        
        Return    : message (string)
        """
        for focus_mode in self.focus_modes:
            if focus_mode['modeName'] == focus_mode_name:
                return focus_mode['message']

    def get_available_lens_modes(self, focus_mode_name=None):
        """
        Descript. :
        """
        if focus_mode_name == None:
            focus_mode_name = self.active_focus_mode
        for focus_mode in self.focus_modes:
            if focus_mode['modeName'] == focus_mode_name:
                return focus_mode['lensModes']   

    def get_lens_combination(self, focus_mode_name=None):
        """
        Descript. :
        """
        if focus_mode_name == None:
            focus_mode_name, beam_size = self.get_active_focus_mode()

        for focus_mode in self.focus_modes:
            if focus_mode['modeName'] == focus_mode_name:
                return focus_mode['lensCombination']

    def get_active_focus_mode(self):
        """
	Descript. : evaluate and get active foc mode
    	Arguments : -                                        
    	Return    : mode name (string or None if unable to detect)
	"""
        if len(self.focus_motors_dict) > 0:
            active_focus_mode = None
            for focus_mode in self.focus_modes:
                self.size = focus_mode['size']
                active_focus_mode = focus_mode['modeName']
                for motor in self.focus_motors_dict:
                    if len(self.focus_motors_dict[motor]) == 0:
                        active_focus_mode = None
                        self.size = [9999, 9999]
                    elif active_focus_mode not in \
                        self.focus_motors_dict[motor]:
                        active_focus_mode = None
                        self.size = [9999, 9999]
                        break
                if active_focus_mode is not None:
                    break
            if active_focus_mode != self.active_focus_mode:
                self.active_focus_mode = active_focus_mode	
                #logging.getLogger("HWR").info('Focusing: %s mode detected' %active_focus_mode)
        return self.active_focus_mode, self.size

    def get_focus_mode(self):
        """
        Descript. :
        """
        if self.active_focus_mode:
            return self.active_focus_mode.lower()

    def set_motor_focus_mode(self, motor_name, focus_mode):	
        """
        Descript. :
        """ 
        if focus_mode is not None:
            for motor in self.motors_groups:
                motor.set_motor_focus_mode(motor_name, focus_mode)

    def set_focus_mode(self, focus_mode):
        """
        Descript. : sets focusing mode
        Arguments : new mode name (string)                                        
        Return    : -
	"""
        if focus_mode and self.cmd_set_phase:
            tinequery(self.cmd_set_phase['address'], 
                      self.cmd_set_phase['property'], 
                      self.cmd_set_phase['argument'])
            if self.motors_groups:		 
                for motors_group in self.motors_groups:
                    motors_group.set_motor_group_focus_mode(focus_mode)
        else:
            #No motors defined
            self.active_focus_mode = focus_mode

    def get_divergence_hor(self):
        """
        Descript. :
        """
        for focus_mode in self.focus_modes:
            if focus_mode['modeName'] == self.active_focus_mode:
                return focus_mode['diverg'][0]

    def get_divergence_ver(self):
        """
        Descript. :
        """
        for focus_mode in self.focus_modes:
            if focus_mode['modeName'] == self.active_focus_mode:
                return focus_mode['diverg'][1]

    def update_values(self):
        """
        Descript. :
        """
        self.emit('focusingModeChanged', self.active_focus_mode, self.size)

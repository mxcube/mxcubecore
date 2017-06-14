"""
[Name] BeamAperture

[Description]
The BeamAperture Hardware Object is used to set and get current aperture.

[Channels]
- self.chanActivePos

[Commands]
- self.cmdChangePos

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
        self.chan_active_position = None
  
        self.beam_focus_hwobj = None

    def init(self):
        """
	Description:
	"""
        for position in self['positions']:
            temp_name = str(position.getProperty('posName'))
            if not temp_name == "Out":
                temp_name = "%s%sm" %(temp_name, unichr(956))
            self.positions_list.append({
                 'origin_name' : str(position.getProperty('posName')),
                 'name'   : temp_name,
                 'modes'  : position.getProperty('modesAllowed'),
                 'size'   : eval(position.getProperty('size'))})
        self.default_position = self.getProperty('defaultPosition')
        self.chan_active_position = self.getChannelObject('CurrentApertureDiameterIndex')
        if self.chan_active_position is not None: 
            self.chan_active_position.connectSignal('update', self.active_position_changed) 	
            self.active_position_changed(self.chan_active_position.getValue())

        if self.getProperty('beamFocusHO') is not None:	
            try:
                self.beam_focus_hwobj = HardwareRepository.HardwareRepository().\
                     getHardwareObject(self.getProperty('beamFocusHO'))
                self.connect(self.beam_focus_hwobj, 'definerPosChanged', \
                     self.beam_focus_changed)
            except:
                logging.getLogger("HWR").debug('BeamAperture: Focusing hwobj not defined')

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

    def update_value(self):
        if self.chan_active_position is not None:
            self.active_position = self.chan_active_position.getValue()
        #if self.beam_focus_hwobj is not None:
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
            and self.chan_active_position:
                self.chan_active_position.setValue(new_position)	
            else:
               #Mockup 
               self.active_position_changed(new_position)
        else:
            if self.chan_active_position:
                self.chan_active_position.setValue(new_position)
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
        return self.positions_list[self.active_position]['origin_name'] 

    def get_aperture_list(self, as_origin=None):
        position_names = []
        if len(self.positions_list) > 0:
            for position in self.positions_list:
                if as_origin:
                    position_names.append(position['origin_name'])
                else:
                    position_names.append(position['name'])
        return position_names        


    def evaluate_aperture(self):	
        """
        Descript. : evaluates aperture position. If aper not allowed sets to default
        Arguments : - 
        Return    : -
        """
        if self.beam_focus_hwobj is None:
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

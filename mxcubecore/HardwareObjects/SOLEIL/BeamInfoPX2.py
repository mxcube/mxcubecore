# -*- coding: utf-8 -*-
"""
[Name] BeamInfo

[Description]
BeamInfo hardware object informs mxCuBE (HutchMenuBrick) about the beam position
and size.

This is the Soleil PX1 version

[Emited signals]

beamInfoChanged
beamPosChanged

[Included Hardware Objects]

[Example XML file]

<device class = "BeaminfoPX2">
  <username>Beamstop</username>
  <channel type="tango" tangoname="i11-ma-cx1/ex/md2" polling="1000" name="beamsizex">BeamSizeHorizontal</channel>
  <channel type="tango" tangoname="i11-ma-cx1/ex/md2" polling="1000" name="beamsizey">BeamSizeVertical</channel>
  <channel type="tango" tangoname="i11-ma-cx1/ex/md2" polling="1000" name="positionx">BeamPositionHorizontal</channel>
  <channel type="tango" tangoname="i11-ma-cx1/ex/md2" polling="1000" name="positiony">BeamPositionVertical</channel>
  <object  role="zoom"  hwrid="/zoom"></object>
</device>



"""

import logging
from HardwareRepository.BaseHardwareObjects import Equipment

class BeamInfoPX2(Equipment):

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.beam_position = [328, 220] #[None, None]
        self.beam_size     = [0.010, 0.005] #[None, None]
        self.shape         = 'rectangular'

        self.beam_info_dict  = {'size_x': None, 'size_y': None, 'shape': self.shape}
        
        self.beam_info_dict['size_x'] = 0.010
        self.beam_info_dict['size_y'] = 0.005
        self.beam_info_dict["shape"] = "ellipse"
        
        # Channels
        self.chanBeamSizeX = None
        self.chanBeamSizeY = None
        self.chanBeamPosX  = None
        self.chanBeamPosY  = None

        # Zoom motor
        self.zoomMotor = None
        #self.minidiff = None
        self.positionTable = {}
       
    def init(self):

        try:
            self.chanBeamSizeX = self.getChannelObject('beamsizex')
            self.chanBeamSizeX.connectSignal('update', self.beamSizeXChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to beamsize x channel ', self.name())

        try:
            self.chanBeamSizeY = self.getChannelObject('beamsizey')
            self.chanBeamSizeY.connectSignal('update', self.beamSizeYChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to beamsize y channel ', self.name())

        try:
            self.chanBeamPosX = self.getChannelObject('positionx')
            self.chanBeamPosX.connectSignal('update', self.beamPosXChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to beamposition x channel ', self.name())

        try:
            self.chanBeamPosY = self.getChannelObject('positiony')
            self.chanBeamPosY.connectSignal('update', self.beamPosYChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to beamposition z channel ', self.name())

        self.zoomMotor = self.getDeviceByRole("zoom")
        
        self.beam_position[0], self.beam_position[1] = self.chanBeamPosX.value, self.chanBeamPosY.value
       
        if self.zoomMotor is not None:
           self.connect(self.zoomMotor, 'predefinedPositionChanged', self.zoomPositionChanged)
        else:
           logging.getLogger().info("Zoom - motor is not good ")

    def beamSizeXChanged(self, value):
        logging.getLogger().info('beamSizeX changed. It is %s ' % value)
        self.beam_size[0] = value
        self.sizeUpdated() 

    def beamSizeYChanged(self, value):
        logging.getLogger().info('beamSizeY changed. It is %s ' % value)
        self.beam_size[1] = value
        self.sizeUpdated() 

    def beamPosXChanged(self, value):
        logging.getLogger().info('beamPosX changed. It is %s ' % value)
        self.beam_position[0] = value
        self.positionUpdated() 

    def beamPosYChanged(self, value):
        logging.getLogger().info('beamPosY changed. It is %s ' % value)
        self.beam_position[1] = value
        self.positionUpdated() 

    def zoomPositionChanged(self, name, offset):
        logging.getLogger().info('zoom position changed. It is %s / offset=%s ' % (name,offset))
        self.beam_position[0], self.beam_position[1] = self.chanBeamPosX.value, self.chanBeamPosY.value

    def sizeUpdated(self):
        #TODO check values give by md2 it appears that  beamSizeXChanged beamSizeYChanged it is not the reality !!!!!!
        self.beam_info_dict['size_x'] = 0.010 # in micro channel in MD2 doesn't work
        self.beam_info_dict['size_y'] = 0.005#
        self.emit("beamInfoChanged", (self.beam_info_dict, ))

    def sizeUpdated2(self):
        # not used
        if None in self.beam_size:
             return
        self.beam_info_dict['size_x'] = self.beam_size[0]
        self.beam_info_dict['size_y'] = self.beam_size[1]
        
        self.emit("beamInfoChanged", (self.beam_info_dict, ))

    def positionUpdated(self):
        self.emit("beamPosChanged", (self.beam_position, ))
        self.sizeUpdated()

    def get_beam_info(self):
        #logging.getLogger().warning('returning beam info It is %s ' % str(self.beam_info_dict))
        return self.beam_info_dict
        
    def get_beam_position(self):
        #logging.getLogger().warning('returning beam positions. It is %s ' % str(self.beam_position))
        return self.beam_position	

    def get_beam_size(self):
        """
        Descript. : returns beam size in millimeters
        Return   : list with two integers
        """
        #self.evaluate_beam_info()
        return self.beam_info_dict["size_x"], \
               self.beam_info_dict["size_y"]
    
    def get_beam_shape(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.evaluate_beam_info()
        return self.beam_info_dict["shape"]
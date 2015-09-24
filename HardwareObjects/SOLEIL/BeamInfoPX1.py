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

<device class = "SoleilBeamInfo">
  <username>Beamstop</username>
  <channel type="tango" tangoname="i10-c-cx1/ex/beamsize" polling="1000" name="beamsizex">sizeX</channel>
  <channel type="tango" tangoname="i10-c-cx1/ex/beamsize" polling="1000" name="beamsizey">sizeZ</channel>
  <channel type="tango" tangoname="i10-c-cx1/ex/beamposition" polling="1000" name="positionx">positionX</channel>
  <channel type="tango" tangoname="i10-c-cx1/ex/beamposition" polling="1000" name="positiony">positionZ</channel>
  <object  role="zoom"  hwrid="/zoom"></object>
</device>



"""

import logging
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Equipment

class BeamInfoPX1(Equipment):

    def __init__(self, *args):
        Equipment.__init__(self, *args)

	self.beam_position = [None, None]
	self.beam_size     = [None, None]
        self.shape         = 'rectangular'

        self.beam_info_dict  = {'size_x': None, 'size_y': None, 'shape': self.shape}

        # Channels
        self.chanBeamSizeX = None
        self.chanBeamSizeY = None
        self.chanBeamPosX  = None
        self.chanBeamPosY  = None

        # Zoom motor
        self.zoomMotor = None
        self.positionTable = {}
       
    def init(self):

        # try:
            # self.chanBeamSizeX = self.getChannelObject('beamsizex')
            # self.chanBeamSizeX.connectSignal('update', self.beamSizeXChanged)
        # except KeyError:
            # logging.getLogger().warning('%s: cannot connect to beamsize x channel ', self.name())
# 
        # try:
            # self.chanBeamSizeY = self.getChannelObject('beamsizey')
            # self.chanBeamSizeY.connectSignal('update', self.beamSizeYChanged)
        # except KeyError:
            # logging.getLogger().warning('%s: cannot connect to beamsize y channel ', self.name())
# 
        # try:
            # self.chanBeamPosX = self.getChannelObject('positionx')
            # self.chanBeamPosX.connectSignal('update', self.beamPosXChanged)
        # except KeyError:
            # logging.getLogger().warning('%s: cannot connect to beamposition x channel ', self.name())
# 
        # try:
            # self.chanBeamPosY = self.getChannelObject('positiony')
            # self.chanBeamPosY.connectSignal('update', self.beamPosYChanged)
        # except KeyError:
            # logging.getLogger().warning('%s: cannot connect to beamposition z channel ', self.name())

        self.zoomMotor = self.getDeviceByRole("zoom")

        if self.zoomMotor is not None:
           logging.getLogger().info("Zoom - motor is good ")
           if self.zoomMotor.hasObject('positions'):
               logging.getLogger().info("Zoom - has positions ")
               for position in self.zoomMotor['positions']:
                   logging.getLogger().info("   - position " + str(position))
                   calibrationData = position['calibrationData']
                   self.positionTable[str(position.offset)] = [ float(calibrationData.beamPositionX), float(calibrationData.beamPositionY) ]
                   logging.getLogger().info("Zoom - beam position table loaded")
                   logging.getLogger().info( str(self.positionTable) )
 
           self.connect(self.zoomMotor, 'predefinedPositionChanged', self.zoomPositionChanged)
           pos = self.zoomMotor.getPosition()
           posname = self.zoomMotor.getCurrentPositionName()
           self.zoomPositionChanged( posname, pos)
        else:
           logging.getLogger().info("Zoom - motor is not good ")


    def beamSizeXChanged(self, value):
        logging.getLogger().info('beamSizeX changed. It is %s ' % value)
        #if value is not None:
        #    self.beam_size[0] = value
        #    self.sizeUpdated() 

    def beamSizeYChanged(self, value):
        logging.getLogger().info('beamSizeY changed. It is %s ' % value)
        #if value is not None:
        #    self.beam_size[1] = value
        #    self.sizeUpdated() 

    def beamPosXChanged(self, value):
        logging.getLogger().info('beamPosX changed. It is %s ' % value)
        #self.beam_position[0] = value
        self.positionUpdated() 

    def beamPosYChanged(self, value):
        logging.getLogger().info('beamPosY changed. It is %s ' % value)
        #self.beam_position[1] = value
        self.positionUpdated() 

    def zoomPositionChanged(self, name, offset):
        logging.getLogger().info('zoom position changed. It is %s / offset=%s ' % (name,offset))
        try:
           offs = str( int(offset) )
           logging.getLogger().info('looking for  offset %s in table. ' % offs)
           logging.getLogger().info(str(self.positionTable))
           if offs in self.positionTable:
              pos = self.positionTable[offs]
              self.beam_position[0], self.beam_position[1] = float(pos[0]), float(pos[1])
              logging.getLogger().info('found %s' % str(self.beam_position))
              self.positionUpdated() 
           else:
              logging.getLogger().info('not found')
        except:
           logging.getLogger().info('not handled')
            
    def sizeUpdated(self):
        self.beam_info_dict['size_x'] = 0.045
        self.beam_info_dict['size_y'] = 0.030
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
        logging.getLogger().warning('returning beam info It is %s ' % str(self.beam_info_dict))
        return self.beam_info_dict
        
    def get_beam_position(self):
        logging.getLogger().warning('returning beam positions. It is %s ' % str(self.beam_position))
	return self.beam_position	


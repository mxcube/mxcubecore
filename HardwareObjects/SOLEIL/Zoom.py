
import TangoDCMotor
import logging
from PyTango import DeviceProxy

class Zoom(TangoDCMotor.TangoDCMotor):

    def init(self):
        
        self.predefinedPositions          = {} 
        self.predefinedLightLevel         = {} 
        self.predefinedPositionsNamesList = []

        self.delta = self.getProperty('delta') or 10
        self.light_dev = DeviceProxy(self.getProperty('tangoname_light')) 

        try:
            positions = self['positions']
        except:
            logging.getLogger().error('%s does not define positions.', str(self.name()))
        else:    
            for definedPosition in positions:
                positionUsername = definedPosition.getProperty('username')

                try:
                    offset = float(definedPosition.getProperty('offset'))
                    light_level = float(definedPosition.getProperty('lightLevel'))
                except:
                    logging.getLogger().warning('%s, ignoring position %s: invalid offset.', str(self.name()), positionUsername)
                else:
                    self.predefinedPositions[positionUsername] = offset 
                    self.predefinedLightLevel[positionUsername] = light_level 

            self.sortPredefinedPositionsList()
            
    def connectNotify(self, signal):

        #TangoDCMotor.TangoDCMotor.connectNotify.im_func(self, signal)
        TangoDCMotor.TangoDCMotor.connectNotify(self, signal)

        if signal == 'predefinedPositionChanged':
            positionName = self.getCurrentPositionName()
            try:
                offset = self.predefinedPositions[positionName]

            except KeyError:
                self.emit(signal, ('', None))
            else:
                self.emit(signal, (positionName, offset))

        elif signal == 'stateChanged':
            self.emit(signal, (self.getState(), ))
            

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(lambda x, y: int(round(self.predefinedPositions[x] - self.predefinedPositions[y])))
                
    def motorMoveDone(self, channelValue):

        TangoDCMotor.TangoDCMotor.motorMoveDone(self, channelValue)
 
        pos = self.getPosition()
        logging.getLogger("HWR").debug("current pos=%s", pos)
 
        for positionName in self.predefinedPositions:
            if self.predefinedPositions[positionName] >= pos-self.delta and self.predefinedPositions[positionName] <= pos+self.delta:
                self.emit('predefinedPositionChanged', (positionName, pos, ))
                return

        self.emit('predefinedPositionChanged', ('', None, ))
         
    def motorPositionChanged(self, channelValue):

        TangoDCMotor.TangoDCMotor.motorPositionChanged(self, channelValue)

        self.emit('predefinedPositionChanged', ('', None, ))
        
    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def moveToPosition(self, positionName):
   
        try:
            self.move(self.predefinedPositions[positionName])
            self.light_dev.intensity = self.predefinedLightLevel[positionName]
        except:
            logging.getLogger().exception('Cannot move motor %s: invalid position name.', str(self.userName()))


    def getCurrentPositionName(self):
        if self.isReady() and self.getState() == self.READY:
            for positionName in self.predefinedPositions:
                if self.predefinedPositions[positionName] >= self.getPosition()-self.delta and self.predefinedPositions[positionName] <= self.getPosition()+self.delta:
                   return positionName 
        return ''


    def setNewPredefinedPosition(self, positionName, positionOffset):
        try:
            self.predefinedPositions[str(positionName)] = float(positionOffset)
            self.sortPredefinedPositionsList()
        except:
            logging.getLogger().exception('Cannot set new predefined position')



from qt import *

from HardwareRepository.BaseHardwareObjects import Device
from TangoDCMotor import TangoDCMotor

import logging

class TangoDCMotorWPositions(TangoDCMotor):

    def __init__(self, name):
        # State values as expected by Motor bricks
        TangoDCMotor.__init__(self, name)

    def _init(self):
        logging.info('__ initializing hw TangoDCMotorWPositions %s' % self.name())
        self.positionChan = self.getChannelObject("position") # utile seulement si positionchan n'est pas defini dans le code
        self.stateChan    = self.getChannelObject("state")    # utile seulement si statechan n'est pas defini dans le code
        self.focus_ho = self.getObjectByRole("focus_motor")
        
        self.positionChan.connectSignal("update", self.positionChanged)
        self.stateChan.connectSignal("update", self.motorStateChanged)
            
        TangoDCMotor._init(self)

    def init(self):
        logging.info('initializing hw TangoDCMotorWPositions 2 %s' % self.name())

        self.predefinedPositions          = {} 
        self.predefinedFocusPositions     = {}
        self.predefinedPositionsNamesList = []

        self.delta = self.getProperty('delta') or 5
        
        try:
            positions = self['positions']
        except:
            logging.getLogger().error('%s does not define positions.', str(self.name()))
        else:    
            for definedPosition in positions:
                positionUsername = definedPosition.getProperty('username')

                try:
                    offset = float(definedPosition.getProperty('offset'))
                except:
                    logging.getLogger().warning('%s, ignoring position %s: invalid offset.', str(self.name()), positionUsername)
                else:
                    self.predefinedPositions[positionUsername] = offset
                
                try:
                    focus_offset = float(definedPosition.getProperty('focus_offset'))
                except:
                    logging.getLogger().warning('%s, ignoring position %s: invalid focus_offset.', str(self.name()), positionUsername)
                else:
                    self.predefinedFocusPositions[positionUsername] = focus_offset 
                    
            self.sortPredefinedPositionsList()
            
        logging.info('TangoDCMotorWPositions self.predefinedPositions %s' % self.predefinedPositions)
        logging.info('TangoDCMotorWPositions self.predefinedFocusPositions %s' % self.predefinedFocusPositions)   
        
    def connectNotifyTO(self, signal):

        if signal == 'predefinedPositionChanged':
            positionName = self.getCurrentPositionName()
            try:
                offset = self.predefinedPositions[positionName]
            except KeyError:
                pass
            else:
                self.emit(signal, (positionName, offset))
        elif signal == 'stateChanged':
            self.emit(signal, (self.getState(), ))
        elif signal == 'zoomPositionChanged':
            self.emit(signal, (self.getZoomLevel(), ))

    def motorStateChanged(self, channelValue):
        TangoDCMotor.motorStateChanged(self, channelValue)
        
    def positionChanged(self, channelValue):
        TangoDCMotor.positionChanged(self, channelValue)
        self.checkPredefinedPosition()
       
    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(lambda x, y: int(round(self.predefinedPositions[x] - self.predefinedPositions[y])))

    def checkPredefinedPosition(self):
        positionName = self.getCurrentPositionName()
        pos = self.getPosition()
        logging.info('checkPredefinedPosition (MY) %s. %s' % (str(positionName), str(pos)) )
        self.emit('predefinedPositionChanged', positionName, pos)

    def getCurrentPositionName(self):
         pos = self.getPosition()
         for positionName in self.predefinedPositions:
             if self.predefinedPositions[positionName] >= pos-self.delta and self.predefinedPositions[positionName] <= pos+self.delta:
                return positionName 
         else:
            return ""

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def moveToPosition(self, positionName):
        logging.getLogger().debug("Moving motor %s to predefined position %s" % ( self.userName(), positionName ))
        try:
            abspos = self.predefinedPositions[positionName]
            try:
                TangoDCMotor.move(self, int(abspos) )
                self.focus_ho.move(self.predefinedFocusPositions[positionName])
            except:
                import traceback
                logging.getLogger().debug("error moving the zoom with offset %s" % traceback.format_exc())
                #TangoDCMotor.move(self, float(abspos) )
                #self.focus.move(self.predefinedFocusPositions[positionName])
            #self.move(self.predefinedPositions[positionName], focus_offset = self.predefinedFocusPositions[positionName])
        except:
            logging.getLogger().exception('Cannot move motor %s: invalid position name.', str(self.userName()))


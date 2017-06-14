
from qt import *

import TangoMotorZoomPX2
import logging
#from SimpleDevice import SimpleDevice

#class TangoMotorWPositionsPX2(TangoMotorZoomPX2.TangoMotorZoomPX2):
class TangoMotorWPositionsPX2(TangoMotorZoomPX2.TangoMotorZoomPX2):
    def init(self):
        
    #        TangoMotorZoomPX2.TangoMotorZoomPX2._init()
        
        self.predefinedPositions = {} 
        self.predefinedPositionsNamesList = []
        self.delta = self.getProperty('delta') or 5
        self.predefinedFocusPositions = {}
        
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
            
            print 
            print 'MS debug 18.10.2012,    self.predefinedPositionsNamesList', self.predefinedPositionsNamesList
            print 'MS debug 18.10.2012,    self.predefinedPositions', self.predefinedPositions
            print 'MS debug 18.10.2012,    self.predefinedFocusPositions', self.predefinedFocusPositions
            print 
    #        try :
    #            self.Zoomdevice = SimpleDevice(self.getProperty("tangoname"), verbose=False)
    #            self.Zoomdevice.waitMoves = True
    #	    self.Zoomdevice.timeout = 5000
    #        except :
    #           self.errorDeviceInstance(self.getProperty("tangoname"))
            

    def connectNotify(self, signal):

        logging.info("zoom connectNotify called for signal %s" % signal)

        TangoMotorZoomPX2.TangoMotorZoomPX2.connectNotify.im_func(self, signal)

        if signal == 'predefinedPositionChanged':
            positionName = self.getCurrentPositionName()
            #print "TangoMotorW",positionName
            try:
                offset = self.predefinedPositions[positionName]
                #print "TangoMotorW",offset

            except KeyError:
                self.emit(signal, ('', None))
            else:
                self.emit(signal, (positionName, offset))
        elif signal == 'stateChanged':
            self.emit(signal, (self.getState(), ))
            
        elif signal == 'zoomPositionChanged':
            self.emit(signal, (self.getZoomLevel(), ))
            

    def motorIsMoving(self):
        if self.getState() == 4:  # Moving
           return True
        else:
           return False
    def getZoomLevel(self):
        return self.device.ZoomLevel, self.device.PhiTableXAxisPosition
        
    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(lambda x, y: int(round(self.predefinedPositions[x] - self.predefinedPositions[y]))) 
                
    def motorMoveDone(self, channelValue):
        logging.getLogger("HWR").debug("Motor move done")
        TangoMotorZoomPX2.TangoMotorZoomPX2.motorMoveDone.im_func(self, channelValue)
        self.checkPredefinedPosition()
    
    def checkPredefinedPosition(self):
        pos = self.getPosition()
        logging.getLogger().debug("current pos=%s", pos)
        for positionName in self.predefinedPositions:
                if self.predefinedPositions[positionName] >= pos-self.delta and self.predefinedPositions[positionName] <= pos+self.delta:
                    logging.info("Motor with predefined positions emitting position signal reached (%s,%s) " % (positionName, pos))
                    self.emit('predefinedPositionChanged', (positionName, pos, ))
                    return
        self.emit('predefinedPositionChanged', ('', None, ))
        
    def motorPositionChanged(self, channelValue):
        TangoMotorZoomPX2.TangoMotorZoomPX2.motorPositionChanged.im_func(self, channelValue)

        #self.emit('predefinedPositionChanged', ('', None, ))
        self.checkPredefinedPosition()
        
    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList


    def moveToPosition(self, positionName):
        #print "TangoMotorW moveToPosition"
        logging.debug("moving prepos motor to  position %s" % positionName)
        try:
            #print 'MS Debug 18.10.2012 self.predefinedPositions', self.predefinedPositions
            self.move(self.predefinedPositions[positionName], focus_offset = self.predefinedFocusPositions[positionName])
            
        except:
            logging.getLogger().exception('Cannot move motor %s: invalid position name.', str(self.userName())) 


    def getCurrentPositionName(self):
        if self.isReady() and self.getState() == self.READY:
            for positionName in self.predefinedPositions:
                if self.predefinedPositions[positionName] >= self.getPosition()-self.delta and self.predefinedPositions[positionName] <= self.getPosition()+self.delta:
                   return positionName 
        return self.device.ZoomLevel #MS 8.2.2013


    def setNewPredefinedPosition(self, positionName, positionOffset):
        try:
            self.predefinedPositions[str(positionName)] = float(positionOffset)
            self.sortPredefinedPositionsList()
        except:
            logging.getLogger().exception('Cannot set new predefined position')


    def move(self, absolutePosition, focus_offset = None):
        """Move the motor to the required position

        Arguments:
        absolutePosition -- position to move to
        """
        if type(absolutePosition) != float and type(absolutePosition) != int:
            logging.getLogger("TangoClient").error("Cannot move %s: position '%s' is not a number", self.device.name, absolutePosition)
            
        #self.__changeMotorState(MOVESTARTED)

        #c = self.connection.getChannel(self.chanNamePrefix % 'start_one')
        logging.getLogger("HWR").info("TangoMotorZoomPX2.move to absolute position: %.3f" % absolutePosition)
        self.device.write_attribute("ZoomLevel", int(absolutePosition))
        #print "focus_offset is", focus_offset
        if focus_offset is not None:
            self.device.write_attribute("PhiTableXAxisPosition", focus_offset)
        print "We're supposed to see zoomPostionChanged signal here"
        self.emit(PYSIGNAL("zoomPositionChanged"), (absolutePosition, focus_offset))












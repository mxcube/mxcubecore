#from MD2Motor import MD2Motor
from HardwareRepository.BaseHardwareObjects import Device
import logging
import math

class MicrodiffZoomMockup(Device):
    #def __init__(self, name):
    #    pass
        #MD2Motor.__init__(self, name)

    def init(self):
        self.motor_name = "Zoom"
        self.motor_pos_attr_suffix = "Position"
        self._last_position_name = None
 
        self.predefined_position_attr = 1

        self.predefinedPositions = { "Zoom 1": 1, "Zoom 2": 2, "Zoom 3": 3, "Zoom 4": 4, "Zoom 5": 5, "Zoom 6": 6, "Zoom 7": 7, "Zoom 8": 8, "Zoom 9": 9, "Zoom 10":10 }
        self.sortPredefinedPositionsList()

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(lambda x, y: int(round(self.predefinedPositions[x] - self.predefinedPositions[y])))

    def connectNotify(self, signal):
        if signal == 'predefinedPositionChanged':
            positionName = self.getCurrentPositionName()

            try:
                pos = self.predefinedPositions[positionName]
            except KeyError:
                self.emit(signal, ('', None))
            else:
                self.emit(signal, (positionName, pos))
        else:
            return True#.connectNotify.im_func(self, signal)
    def getState(self):
    	return 2
    def getLimits(self):
        return (1,10)

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def motorPositionChanged(self, absolutePosition, private={}):
        #MD2Motor.motorPositionChanged.im_func(self, absolutePosition, private)
        positionName = self.getCurrentPositionName(absolutePosition)
        if self._last_position_name != positionName:
            self._last_position_name = positionName
            self.emit('predefinedPositionChanged', (positionName, positionName and absolutePosition or None, ))
    def getCurrentPositionName(self, pos=None):
        pos = self.predefined_position_attr

        for positionName in self.predefinedPositions:
          if math.fabs(self.predefinedPositions[positionName] - pos) <= 1E-3:
            return positionName
        return ''          
    def moveToPosition(self, positionName):
        try:
            self.predefined_position_attr = self.predefinedPositions[positionName]
            return True
        except:
            return False


from MD2Motor import MD2Motor
import logging
import math

class MicrodiffZoom(MD2Motor):
    def __init__(self, name):
        MD2Motor.__init__(self, name)

    def init(self):
        self.motor_name = "Zoom"
        self.motor_pos_attr_suffix = "Position"
        self._last_position_name = None
 
        MD2Motor.init(self)

        self.predefined_position_attr = self.addChannel({"type":"exporter", "name":"predefined_position"  }, "CoaxialCameraZoomValue")

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
            return MD2Motor.connectNotify.im_func(self, signal)

    def getLimits(self):
        return (1,10)

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def motorPositionChanged(self, absolutePosition, private={}):
        MD2Motor.motorPositionChanged.im_func(self, absolutePosition, private)

        positionName = self.getCurrentPositionName(absolutePosition)
        if self._last_position_name != positionName:
          self._last_position_name = positionName
          self.emit('predefinedPositionChanged', (positionName, positionName and absolutePosition or None, ))

    def getCurrentPositionName(self, pos=None):
        pos = self.predefined_position_attr.getValue()

        for positionName in self.predefinedPositions:
          if math.fabs(self.predefinedPositions[positionName] - pos) <= 1E-3:
            return positionName
        return ''

    def moveToPosition(self, positionName):
        #logging.getLogger().debug("%s: trying to move %s to %s:%f", self.name(), self.motor_name, positionName,self.predefinedPositions[positionName])
        try:
            self.predefined_position_attr.setValue(self.predefinedPositions[positionName])
        except:
            logging.getLogger("HWR").exception('Cannot move motor %s: invalid position name.', str(self.userName()))

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError

    def zoom_in(self):
        position_name = self.getCurrentPositionName()
        position_index = self.predefinedPositionsNamesList.index(position_name)
        if position_index < len(self.predefinedPositionsNamesList) - 1:
            self.moveToPosition(self.predefinedPositionsNamesList[position_index + 1])
 
    def zoom_out(self):
        position_name = self.getCurrentPositionName()
        position_index = self.predefinedPositionsNamesList.index(position_name)
        if position_index > 0:
            self.moveToPosition(self.predefinedPositionsNamesList[position_index - 1])


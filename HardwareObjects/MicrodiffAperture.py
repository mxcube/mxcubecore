from MicrodiffMotorr import MicrodiffMotor
import logging
import math

class MicrodiffAperture(MicrodiffMotor):
    def __init__(self, name):
        MicrodiffMotor.__init__(self, name)

    def init(self):
        self.motor_name = "CurrentApertureDiameter"
        self.motor_pos_attr_suffix = "Index"

        self.aperture_inout = self.getObjectByRole('inout')
        self.predefinedPositions = {}
        self.labels = self.addChannel({"type":"exporter", "name":"ap_labels" }, "ApertureDiameters")
        self.filters = self.labels.getValue()
        self.nb = len(self.filters)
        j = 0
        while j < self.nb :
          for i in self.filters:
            if int(i) >= 300:
                i = "Outbeam"
            self.predefinedPositions[str(i)] = j
            j = j+1
        if not "Outbeam" in self.predefinedPositions:
            self.predefinedPositions["Outbeam"] = self.predefinedPositions.__len__()
        self.predefinedPositions.pop("Outbeam")
        self.sortPredefinedPositionsList()
        MicrodiffMotor.init(self)
        
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
        elif signal == 'apertureChanged':
                self.emit('apertureChanged', (self.getApertureSize(), ))
        else:
            return MicrodiffMotor.connectNotify.im_func(self, signal)

    def getLimits(self):
        return (1,self.nb)

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def motorPositionChanged(self, absolutePosition, private={}):
        MicrodiffMotor.motorPositionChanged.im_func(self, absolutePosition, private)

        positionName = self.getCurrentPositionName(absolutePosition)
        self.emit('predefinedPositionChanged', (positionName, positionName and absolutePosition or None, ))
        self.emit('apertureChanged', (self.getApertureSize(), ))

    def getCurrentPositionName(self, pos=None):
        if self.getPosition() is not None:
            pos = pos or self.getPosition()
        else:
            pos = pos

        try:
            for positionName in self.predefinedPositions:
                if math.fabs(self.predefinedPositions[positionName] - pos) <= 1E-3:
                    return positionName
        except:
            return ''

    def moveToPosition(self, positionName):
        logging.getLogger().debug("%s: trying to move %s to %s:%f", self.name(), self.motor_name, positionName,self.predefinedPositions[positionName])

        if positionName == 'Outbeam':
            self.aperture_inout.actuatorOut()
        else:
            try:
                self.move(self.predefinedPositions[positionName], wait=True, timeout=10)
            except:
                logging.getLogger("HWR").exception('Cannot move motor %s: invalid position name.', str(self.userName()))
            if self.aperture_inout.getActuatorState() != 'in':
                self.aperture_inout.actuatorIn()

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError

    def getApertureSize(self):
        diameter_name = self.getCurrentPositionName()
        for diameter in self["diameter"]:
            if str(diameter.getProperty("name")) == str(diameter_name):
                return (diameter.getProperty("size"),)*2
        return (9999,9999)

    def getApertureCoef(self):
        diameter_name = self.getCurrentPositionName()
        for diameter in self["diameter"]:
            if str(diameter.getProperty("name")) == str(diameter_name):
                aperture_coef = diameter.getProperty("aperture_coef")
                return float(aperture_coef)
        return 1

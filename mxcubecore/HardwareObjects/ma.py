import logging
import math

from HardwareRepository.HardwareObjects.ExporterMotor import ExporterMotor
from warnings import warn


class MicrodiffAperture(ExporterMotor):
    def __init__(self, name):
        ExporterMotor.__init__(self, name)

    def init(self):
        self.actuator_name = "CurrentApertureDiameter"
        self.motor_pos_attr_suffix = "Index"

        self.aperture_inout = self.getObjectByRole("inout")
        self.predefinedPositions = {}
        self.labels = self.addChannel(
            {"type": "exporter", "name": "ap_labels"}, "ApertureDiameters"
        )
        self.filters = self.labels.getValue()
        self.nb = len(list(self.filters))
        j = 0
        while j < self.nb:
            for i in self.filters:
                if int(i) >= 300:
                    i = "Outbeam"
                self.predefinedPositions[str(i)] = j
                j = j + 1
        if "Outbeam" not in self.predefinedPositions:
            self.predefinedPositions["Outbeam"] = self.predefinedPositions.__len__()
        self.predefinedPositions.pop("Outbeam")
        self.sortPredefinedPositionsList()
        ExporterMotor.init(self)

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = [
            int(n) for n in self.predefinedPositions.keys()
        ]
        self.predefinedPositionsNamesList = sorted(
            self.predefinedPositionsNamesList, reverse=True
        )

    def connectNotify(self, signal):
        if signal == "predefinedPositionChanged":
            positionName = self.getCurrentPositionName()
            try:
                pos = self.predefinedPositions[positionName]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (positionName, pos))
            self.emit("apertureChanged", (self.getApertureSize(),))
        else:
            return ExporterMotor.connectNotify(self, signal)

    def get_limits(self):
        return (1, self.nb)

    def get_diameter_size_list(self):
        return self.predefinedPositionsNamesList

    def getPredefinedPositionsList(self):
        warn(
            "getPredefinedPositionsList is deprecated. Use get_diameter_size_list() instead",
            DeprecationWarning,
        )

        return get_diameter_size_list()

    def update_position(self, position, private={}):
        ExporterMotor.update_position(position)

        positionName = self.getCurrentPositionName(position)
        self.emit(
            "predefinedPositionChanged",
            (positionName, positionName and position or None),
        )
        self.emit("apertureChanged", (self.getApertureSize(),))

    def get_diameter_size(self, pos=None):
        if self.get_value() is not None:
            pos = pos or self.get_value()
        else:
            pos = pos

        try:
            for positionName in self.predefinedPositions:
                if math.fabs(self.predefinedPositions[positionName] - pos) <= 1e-3:
                    return positionName
        except BaseException:
            return ""

    def getCurrentPositionName(self, pos=None):
        warn(
            "getCurrentPositionName is deprecated. Use get_diameter_size() instead",
            DeprecationWarning,
        )

        return self.get_diameter_size(pos)

    def moveToPosition(self, positionName):
        logging.getLogger().debug(
            "%s: trying to move %s to %s:%f",
            self.name(),
            self.actuator_name,
            positionName,
            self.predefinedPositions[positionName],
        )

        if positionName == "Outbeam":
            self.aperture_inout.actuatorOut()
        else:
            try:
                self.set_value(
                    self.predefinedPositions[positionName], wait=True, timeout=10
                )
            except BaseException:
                logging.getLogger("HWR").exception(
                    "Cannot move motor %s: invalid position name.", str(self.userName())
                )
            if self.aperture_inout.getActuatorState() != "in":
                self.aperture_inout.actuatorIn()

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError

    def getApertureSize(self):
        diameter_name = self.getCurrentPositionName()
        for diameter in self["diameter"]:
            if str(diameter.getProperty("name")) == str(diameter_name):
                return (diameter.getProperty("size"),) * 2
        return (9999, 9999)

    def getApertureCoef(self):
        diameter_name = self.getCurrentPositionName()
        for diameter in self["diameter"]:
            if str(diameter.getProperty("name")) == str(diameter_name):
                aperture_coef = diameter.getProperty("aperture_coef")
                return float(aperture_coef)
        return 1

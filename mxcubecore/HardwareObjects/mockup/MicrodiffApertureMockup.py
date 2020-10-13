# from MD2Motor import MD2Motor
from HardwareRepository.BaseHardwareObjects import Device
import math


class MicrodiffApertureMockup(Device):
    def init(self):
        self.actuator_name = "CurrentApertureDiameter"
        self.motor_pos_attr_suffix = "Index"
        self._last_position_name = None

        self.predefined_position_attr = 1

        self.predefinedPositions = {"5": 1, "20": 2, "50": 3, "100": 4, "150": 5}
        self.sortPredefinedPositionsList()

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(
            lambda x, y: int(
                round(self.predefinedPositions[x] - self.predefinedPositions[y])
            )
        )

    def connect_notify(self, signal):
        if signal == "predefinedPositionChanged":
            positionName = self.get_current_position_name()

            try:
                pos = self.predefinedPositions[positionName]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (positionName, pos))
        else:
            return True

    def get_state(self):
        return 2

    def get_limits(self):
        return (1, 5)

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def motorPositionChanged(self, absolutePosition, private={}):
        # MD2Motor.motorPositionChanged.im_func(self, absolutePosition, private)
        positionName = self.get_current_position_name(absolutePosition)
        if self._last_position_name != positionName:
            self._last_position_name = positionName
            self.emit(
                "predefinedPositionChanged",
                (positionName, positionName and absolutePosition or None),
            )

    def get_current_position_name(self, pos=None):
        pos = self.predefined_position_attr

        for positionName in self.predefinedPositions:
            if math.fabs(self.predefinedPositions[positionName] - pos) <= 1e-3:
                return positionName
        return ""

    def moveToPosition(self, positionName):
        try:
            self.predefined_position_attr = self.predefinedPositions[positionName]
            return True
        except Exception:
            return False

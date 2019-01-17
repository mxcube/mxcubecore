# from MD2Motor import MD2Motor
from HardwareRepository.BaseHardwareObjects import Device
import logging
import math


class MicrodiffZoomMockup(Device):

    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def init(self):
        self.motor_name = "Zoom"
        self.motor_pos_attr_suffix = "Position"
        self._last_position_name = None

        self.predefined_position_attr = 1

        self.predefinedPositions = {
            "Zoom 1": 1,
            "Zoom 2": 2,
            "Zoom 3": 3,
            "Zoom 4": 4,
            "Zoom 5": 5,
            "Zoom 6": 6,
            "Zoom 7": 7,
            "Zoom 8": 8,
            "Zoom 9": 9,
            "Zoom 10": 10,
        }
        self.sortPredefinedPositionsList()

        self.get_state = self.getState
        self.get_predefined_positions_list = self.getPredefinedPositionsList
        self.get_current_position_name = self.getCurrentPositionName
        self.move_to_position = self.moveToPosition

    def isReady(self):
        return True

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        if hasattr(self.predefinedPositionsNamesList, "sort"):  
            self.predefinedPositionsNamesList.sort(
                lambda x, y: int(
                    round(self.predefinedPositions[x] - self.predefinedPositions[y])
                )
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
        else:
            return True  # .connectNotify.im_func(self, signal)

    def getState(self):
        return 2

    def getLimits(self):
        return (1, 10)

    def getState(self):
        return MicrodiffZoomMockup.READY

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def motorPositionChanged(self, absolutePosition, private={}):
        # MD2Motor.motorPositionChanged.im_func(self, absolutePosition, private)
        positionName = self.getCurrentPositionName(absolutePosition)
        if self._last_position_name != positionName:
            self._last_position_name = positionName
            self.emit(
                "predefinedPositionChanged",
                (positionName, positionName and absolutePosition or None),
            )

    def getCurrentPositionName(self, pos=None):
        pos = self.predefined_position_attr

        for positionName in self.predefinedPositions:
            if math.fabs(self.predefinedPositions[positionName] - pos) <= 1e-3:
                return positionName
        return ""

    def moveToPosition(self, positionName):
        valid = True

        try:
            self.predefined_position_attr = self.predefinedPositions[positionName]
            self.motorPositionChanged(self.predefined_position_attr)
            return True
        except BaseException:
            valid = False

        self.connectNotify("predefinedPositionChanged")
        return valid

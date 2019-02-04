
import SpecMotor
import logging


class SpecMotorWPositions(SpecMotor.SpecMotor):
    def init(self):
        self.predefinedPositions = {}
        self.predefinedPositionsNamesList = []
        self.delta = self.getProperty("delta") or 0

        try:
            positions = self["positions"]
        except BaseException:
            logging.getLogger("HWR").error(
                "%s does not define positions.", str(self.name())
            )
        else:
            for definedPosition in positions:
                positionUsername = definedPosition.getProperty("username")

                try:
                    offset = float(definedPosition.getProperty("offset"))
                except BaseException:
                    logging.getLogger("HWR").warning(
                        "%s, ignoring position %s: invalid offset.",
                        str(self.name()),
                        positionUsername,
                    )
                else:
                    self.predefinedPositions[positionUsername] = offset

            self.sortPredefinedPositionsList()

    def connectNotify(self, signal):
        SpecMotor.SpecMotor.connectNotify.__func__(self, signal)

        if signal == "predefinedPositionChanged":
            positionName = self.getCurrentPositionName()

            try:
                pos = self.predefinedPositions[positionName]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (positionName, pos))
        elif signal == "stateChanged":
            self.emit(signal, (self.getState(),))

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = list(self.predefinedPositions.keys())
        self.predefinedPositionsNamesList.sort(
            lambda x, y: int(
                round(self.predefinedPositions[x] - self.predefinedPositions[y])
            )
        )

    def motorMoveDone(self, channelValue):
        SpecMotor.SpecMotor.motorMoveDone.__func__(self, channelValue)

        pos = self.getPosition()
        logging.getLogger("HWR").debug("current pos=%s", pos)

        for positionName in self.predefinedPositions:
            if (
                self.predefinedPositions[positionName] >= pos - self.delta
                and self.predefinedPositions[positionName] <= pos + self.delta
            ):
                self.emit("predefinedPositionChanged", (positionName, pos))
                return

        self.emit("predefinedPositionChanged", ("", None))

    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList

    def moveToPosition(self, positionName):
        try:
            self.move(self.predefinedPositions[positionName])
        except BaseException:
            logging.getLogger("HWR").exception(
                "Cannot move motor %s: invalid position name.", str(self.userName())
            )

    def getCurrentPositionName(self):
        if (
            not self.motorIsMoving()
        ):  # self.isReady() and self.getState() == self.READY:
            for positionName in self.predefinedPositions:
                if (
                    self.predefinedPositions[positionName]
                    >= self.getPosition() - self.delta
                    and self.predefinedPositions[positionName]
                    <= self.getPosition() + self.delta
                ):
                    return positionName
        return ""

    def setNewPredefinedPosition(self, positionName, positionOffset):
        try:
            self.predefinedPositions[str(positionName)] = float(positionOffset)
            self.sortPredefinedPositionsList()
        except BaseException:
            logging.getLogger("HWR").exception("Cannot set new predefined position")

from warnings import warn
from BlissMotor import BlissMotor
import logging


class BlissMotorWPositions(BlissMotor):
    def __init__(self, name):
        warn(
            "BlissMotorWPositions class is deprecated. Use BlissNState instead",
            DeprecationWarning,
        )
        BlissMotor.__init__(self, name)

    def init(self):
        BlissMotor.init(self)

        self.predefinedPositions = {}
        self.predefinedPositionsNamesList = []
        self.delta = self.get_property("delta") or 0

        try:
            positions = self["positions"]
        except Exception:
            logging.getLogger("HWR").error(
                "%s does not define positions.", str(self.name())
            )
        else:
            for definedPosition in positions:
                positionUsername = definedPosition.get_property("username")

                try:
                    offset = float(definedPosition.get_property("offset"))
                except Exception:
                    logging.getLogger("HWR").warning(
                        "%s, ignoring position %s: invalid offset.",
                        str(self.name()),
                        positionUsername,
                    )
                else:
                    self.predefinedPositions[positionUsername] = offset

            self.sortPredefinedPositionsList()

    def getPositionsData(self):
        return self["positions"]

    def connect_notify(self, signal):
        BlissMotor.connect_notify(self, signal)

        if signal == "predefinedPositionChanged":
            positionName = self.get_current_position_name()

            try:
                pos = self.predefinedPositions[positionName]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (positionName, pos))
        elif signal == "stateChanged":
            self.emit(signal, (self.get_state(),))

    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = self.predefinedPositions.keys()
        self.predefinedPositionsNamesList.sort(
            lambda x, y: int(
                round(self.predefinedPositions[x] - self.predefinedPositions[y])
            )
        )

    def updateState(self, state=None):
        prev_state = self.motorState

        BlissMotor.updateState(self, state)

        if self.motorState != prev_state and self.motorState == BlissMotor.READY:
            pos = self.get_value()

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
            self.set_value(self.predefinedPositions[positionName])
        except Exception:
            logging.getLogger("HWR").exception(
                "Cannot move motor %s: invalid position name.", str(self.username)
            )

    def get_current_position_name(self):
        if (
            not self.motorIsMoving()
        ):  # self.is_ready() and self.get_state() == self.READY:
            for positionName in self.predefinedPositions:
                if (
                    self.predefinedPositions[positionName]
                    >= self.get_value() - self.delta
                    and self.predefinedPositions[positionName]
                    <= self.get_value() + self.delta
                ):
                    return positionName
        return ""

    def setNewPredefinedPosition(self, positionName, positionOffset):
        try:
            self.predefinedPositions[str(positionName)] = float(positionOffset)
            self.sortPredefinedPositionsList()
        except Exception:
            logging.getLogger("HWR").exception("Cannot set new predefined position")

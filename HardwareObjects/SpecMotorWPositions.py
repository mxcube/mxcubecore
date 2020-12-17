from mx3core.HardwareObjects import SpecMotor
import logging


class SpecMotorWPositions(SpecMotor.SpecMotor):
    def init(self):
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

    def connect_notify(self, signal):
        SpecMotor.SpecMotor.connect_notify.__func__(self, signal)

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
        self.predefinedPositionsNamesList = list(self.predefinedPositions.keys())
        self.predefinedPositionsNamesList.sort(
            lambda x, y: int(
                round(self.predefinedPositions[x] - self.predefinedPositions[y])
            )
        )

    def motorMoveDone(self, channelValue):
        SpecMotor.SpecMotor.motorMoveDone.__func__(self, channelValue)

        pos = self.get_value()
        logging.getLogger("HWR").debug("current pos=%s", pos)

        for positionName in self.predefinedPositions:
            if (
                self.predefinedPositions[positionName] >= pos - self.delta
                and self.predefinedPositions[positionName] <= pos + self.delta
            ):
                self.emit("predefinedPositionChanged", (positionName, pos))
                return

        self.emit("predefinedPositionChanged", ("", None))

    def get_predefined_positions_list(self):
        return self.predefinedPositionsNamesList

    def moveToPosition(self, positionName):
        try:
            self.move(self.predefinedPositions[positionName])
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

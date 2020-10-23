import logging
from HardwareRepository.HardwareObjects.MicrodiffAperture import MicrodiffAperture


class BIOMAXAperture(MicrodiffAperture):

    POSITIONS = ("BEAM", "OFF", "PARK")

    def __init__(self, *args):
        MicrodiffAperture.__init__(self, *args)
        self.aperture_position = None

    def init(self):
        MicrodiffAperture.init(self)
        self.aperture_position = self.add_channel(
            {"type": "exporter", "name": "AperturePosition"}, "AperturePosition"
        )
        if self.aperture_position is not None:
            self.connect(self.aperture_position, "update", self.position_changed)

        self.get_diameter_size_list = self.get_predefined_positions_list
        self.set_position = self.moveToPosition

    def moveToPosition(self, positionName):
        logging.getLogger().debug(
            "%s: trying to move %s to %s:%f",
            self.name(),
            self.motor_name,
            positionName,
            self.predefinedPositions[positionName],
        )
        if positionName == "Outbeam":
            self.aperture_position.set_value("OFF")
        else:
            try:
                self.set_value(
                    self.predefinedPositions[positionName], wait=True, timeout=10
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "Cannot move motor %s: invalid position name.", str(self.username)
                )
            if self.aperture_position.get_value() != "BEAM":
                self.aperture_position.set_value("BEAM")

    def get_position_list(self):
        return BIOMAXAperture.POSITIONS

    def position_changed(self, position):
        self.emit("valueChanged", position)  # self.aperture_position.get_value())

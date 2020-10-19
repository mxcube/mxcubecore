from HardwareRepository.HardwareObjects import MultiplePositions


class MinidiffAperture(MultiplePositions.MultiplePositions):
    def __init__(self, *args, **kwargs):
        MultiplePositions.MultiplePositions.__init__(self, *args, **kwargs)

    def getApertureCoef(self):
        current_pos = self.get_value()
        for position in self["positions"]:
            if position.get_property("name") == current_pos:
                aperture_coef = position.get_property("aperture_coef")
                return aperture_coef
        return 1

    def getApertureSize(self):
        current_pos = self.get_value()
        for position in self["positions"]:
            if position.get_property("name") == current_pos:
                aperture_size = float(position.get_property("aperture_size"))

                if aperture_size > 1:
                    # aperture size in microns
                    return (aperture_size / 1000.0, aperture_size / 1000.0)
                else:
                    # aperture size in millimeters
                    return (aperture_size, aperture_size)
        return (9999, 9999)

    def connect_notify(self, signal):
        if signal == "apertureChanged":
            self.checkPosition()

    def checkPosition(self, *args):
        pos = MultiplePositions.MultiplePositions.checkPosition(self, *args)

        self.emit("apertureChanged", (self.getApertureSize(),))

        return pos

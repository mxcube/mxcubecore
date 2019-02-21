from HardwareRepository.HardwareObjects import MultiplePositions


class MinidiffAperture(MultiplePositions.MultiplePositions):
    def __init__(self, *args, **kwargs):
        MultiplePositions.MultiplePositions.__init__(self, *args, **kwargs)

    def getApertureCoef(self):
        current_pos = self.getPosition()
        for position in self["positions"]:
            if position.getProperty("name") == current_pos:
                aperture_coef = position.getProperty("aperture_coef")
                return aperture_coef
        return 1

    def getApertureSize(self):
        current_pos = self.getPosition()
        for position in self["positions"]:
            if position.getProperty("name") == current_pos:
                aperture_size = float(position.getProperty("aperture_size"))

                if aperture_size > 1:
                    # aperture size in microns
                    return (aperture_size / 1000.0, aperture_size / 1000.0)
                else:
                    # aperture size in millimeters
                    return (aperture_size, aperture_size)
        return (9999, 9999)

    def connectNotify(self, signal):
        if signal == "apertureChanged":
            self.checkPosition()

    def checkPosition(self, *args):
        pos = MultiplePositions.MultiplePositions.checkPosition(self, *args)

        self.emit("apertureChanged", (self.getApertureSize(),))

        return pos

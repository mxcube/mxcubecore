from HardwareRepository.HardwareObjects import MultiplePositions
import logging

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


    

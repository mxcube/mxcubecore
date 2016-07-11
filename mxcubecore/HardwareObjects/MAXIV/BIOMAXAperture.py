import logging
from HardwareRepository import HardwareRepository
from MicrodiffAperture import MicrodiffAperture

class BIOMAXAperture(MicrodiffAperture):
    def __init__(self, *args):
        MicrodiffAperture.__init__(self, *args)

    def init(self): 
        MicrodiffAperture.init(self)
        self.aperture_position = self.addChannel({"type":"exporter", "name":"AperturePosition" }, "AperturePosition")
        print self.aperture_position

    def moveToPosition(self, positionName):
        logging.getLogger().debug("%s: trying to move %s to %s:%f", self.name(), self.motor_name, positionName,self.predefinedPositions[positionName])
        if positionName == 'Outbeam':
            self.aperture_position.setValue("OFF")
        else:
            try:
                self.move(self.predefinedPositions[positionName], wait=True, timeout=10)
            except:
                logging.getLogger("HWR").exception('Cannot move motor %s: invalid position name.', str(self.userName()))
            if self.aperture_position.getValue() != 'BEAM':
                self.aperture_position.setValue("BEAM")


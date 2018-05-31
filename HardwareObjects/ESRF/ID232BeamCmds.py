from HardwareRepository.BaseHardwareObjects import HardwareObject
from BeamCmds import (ControllerCommand)        

class ID232BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)

    def getCommands(self):
        return [self.centrebeam]

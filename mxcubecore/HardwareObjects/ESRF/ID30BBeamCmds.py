from HardwareRepository.BaseHardwareObjects import HardwareObject
from BeamCmds import ControllerCommand, HWObjActuatorCommand


class ID30BBeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.getObjectByRole("controller")
        controller.detcover.set_in()
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        self.quick_realign = ControllerCommand(
            "Quick realign", controller.quick_realign
        )
        self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)

    def getCommands(self):
        return [self.centrebeam, self.quick_realign, self.anneal]

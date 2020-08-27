from HardwareRepository.BaseHardwareObjects import HardwareObject
from .BeamCmds import ControllerCommand, HWObjActuatorCommand


class ID232BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.getObjectByRole("controller")
        detcover = self.getObjectByRole("detcover")
        scintillator = self.getObjectByRole("scintillator")
        hutchtrigger = self.getObjectByRole("hutchtrigger")
        cryo = self.getObjectByRole("cryo")

        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        self.anneal = ControllerCommand("Anneal", controller.anneal)

        self.detcover = HWObjActuatorCommand("Detector cover", detcover)
        self.scintillator = HWObjActuatorCommand("Scintillator", scintillator)
        self.hutchtrigger = HWObjActuatorCommand("Hutchtrigger", hutchtrigger)
        self.cryo = HWObjActuatorCommand("Cryo", cryo)

    def get_commands(self):
        return [
            self.centrebeam,
            self.anneal,
            self.detcover,
            self.scintillator,
            self.hutchtrigger,
            self.cryo,
        ]

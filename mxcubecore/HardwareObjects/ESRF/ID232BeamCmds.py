from HardwareRepository.BaseHardwareObjects import HardwareObject
from .BeamCmds import ControllerCommand, HWObjActuatorCommand


class ID232BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.get_object_by_role("controller")
        detcover = self.get_object_by_role("detcover")
        scintillator = self.get_object_by_role("scintillator")
        hutchtrigger = self.get_object_by_role("hutchtrigger")
        cryo = self.get_object_by_role("cryo")

        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)

        self.detcover = HWObjActuatorCommand("Detector cover", detcover)
        self.scintillator = HWObjActuatorCommand("Scintillator", scintillator)
        self.hutchtrigger = HWObjActuatorCommand("Hutchtrigger", hutchtrigger)
        self.cryo = HWObjActuatorCommand("Cryo", cryo)

    def get_commands(self):
        return [
            self.centrebeam,
            self.detcover,
            self.scintillator,
            self.hutchtrigger,
            self.cryo,
        ]

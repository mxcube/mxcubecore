from mx3core.BaseHardwareObjects import HardwareObject
from .BeamCmds import ControllerCommand, HWObjActuatorCommand


class ID29BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.get_object_by_role("controller")
        detcover = self.get_object_by_role("detcover")
        scintilator = self.get_object_by_role("scintilator")
        aperture = self.get_object_by_role("aperture")
        hutchtrigger = self.get_object_by_role("hutchtrigger")
        cryo = self.get_object_by_role("cryo")

        controller.detcover.set_in()
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        self.quick_realign = ControllerCommand(
            "Quick realign", controller.quick_realign
        )
        self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)

        self.detcover = HWObjActuatorCommand("Detector cover", detcover)
        self.scintilator = HWObjActuatorCommand("Scintillator", scintilator)
        self.aperture = HWObjActuatorCommand("Aperture", aperture)
        self.hutchtrigger = HWObjActuatorCommand("Hutchtrigger", hutchtrigger)
        self.cryo = HWObjActuatorCommand("Cryo", cryo)

    def get_commands(self):
        return [
            self.centrebeam,
            self.quick_realign,
            self.anneal,
            self.detcover,
            self.scintilator,
            self.aperture,
            self.hutchtrigger,
            self.cryo,
        ]

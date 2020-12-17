from mx3core.BaseHardwareObjects import HardwareObject
from .BeamCmds import ControllerCommand


class ID30A3BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.get_object_by_role("controller")
        controller.detcover.set_in()
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        self.quick_realign = ControllerCommand(
            "Quick realign", controller.quick_realign
        )
        self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)
        self.jetvideo = ControllerCommand("Jet video", controller.jet_video)

    def get_commands(self):
        return [self.centrebeam, self.quick_realign, self.anneal, self.jetvideo]

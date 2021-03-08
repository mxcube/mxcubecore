from mxcubecore.BaseHardwareObjects import HardwareObject
from .BeamCmds import ControllerCommand, TestCommand, HWObjActuatorCommand


class ID30BBeamCmds(HardwareObject):
    """Beam action commands for ID30-A3"""
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.get_object_by_role("controller")
        controller.detcover.set_in()
        self.centrebeam = ControllerCommand("Centre beam", controller.centrebeam)
        hutchtrigger = self.get_object_by_role("hutchtrigger")
        if hutchtrigger:
            self.hutchtrigger = HWObjActuatorCommand("Hutchtrigger", hutchtrigger)

        detector_cover = self.get_object_by_role("detector_cover")
        if detector_cover:
            self.detcover = HWObjActuatorCommand("Detector Cover", detector_cover)
        self.test_cmd = TestCommand("Test command")
        # self.quick_realign = ControllerCommand(
        #   "Quick realign", controller.quick_realign
        # )
        # self.anneal = ControllerCommand("Anneal", controller.anneal_procedure)

    def get_commands(self):
        return [self.centrebeam] #self.hutchtrigger]#, self.detcover]

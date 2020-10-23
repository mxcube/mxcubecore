from HardwareRepository.BaseHardwareObjects import HardwareObject


class RobodiffController(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self, *args):
        self.__controller = self.get_object_by_role("controller").robot

    def set_diagfile(self, diagfile):
        self.__controller.diagfile = diagfile

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        return getattr(self.__controller, attr)

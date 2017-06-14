from HardwareRepository.BaseHardwareObjects import HardwareObject

class UnitTest(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        for role in self.getRoles():
            hwobj = self.getObjectByRole(role)
            setattr(self, role + '_hwobj', hwobj)

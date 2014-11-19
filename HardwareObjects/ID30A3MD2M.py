from HardwareRepository.TaskUtils import *
import MiniDiff

class ID30A3MD2M(MiniDiff.MiniDiff):      
    def __init__(self, name):
        MiniDiff.MiniDiff.__init__(self, name)

    def init(self): 
        self.controller = self.getObjectByRole("controller")
        MiniDiff.MiniDiff.init(self)

    def oscil(self, *args, **kwargs):
        self.controller.oscil(*args, **kwargs)

    def helical_oscil(self, *args, **kwargs):
        self.controller.helical_oscil(*args, **kwargs)


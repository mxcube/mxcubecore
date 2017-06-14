import DataAnalysis
from HardwareRepository.BaseHardwareObjects import HardwareObject

class EMBLDataAnalysis(DataAnalysis.DataAnalysis, HardwareObject):
    #Test
    def get_beam_size(self):
        return (0.1,0.2) #(self.execute_command("get_beam_size_x"),
               # self.execute_command("get_beam_size_y"))

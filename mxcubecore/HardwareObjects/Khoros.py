from HardwareRepository.BaseHardwareObjects import HardwareObject
import os
import sys
import khoros

class Khoros(HardwareObject):
  def __init__(self, *args):
    HardwareObject.__init__(self, *args)

  def init(self, *args):  
     setup_file = self.getProperty("setup_file")

     khoros.setup(setup_file, self.__dict__)

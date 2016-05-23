from HardwareRepository.BaseHardwareObjects import HardwareObject
import os
import sys
from bliss.shell import setup

class Bliss(HardwareObject):
  def __init__(self, *args):
    HardwareObject.__init__(self, *args)

  def init(self, *args):  
     setup_file = self.getProperty("setup_file")

     setup(setup_file, self.__dict__)

from HardwareRepository.BaseHardwareObjects import HardwareObject
import os
import sys
from bliss.config import static

class Bliss(HardwareObject):
  def __init__(self, *args):
    HardwareObject.__init__(self, *args)

  def init(self, *args):
     cfg = static.get_config()
     session = cfg.get(self.getProperty("session"))

     session.setup(self.__dict__, verbose=True)

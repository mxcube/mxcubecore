from HardwareRepository.BaseHardwareObjects import HardwareObject
import os
import sys

class RobodiffController(HardwareObject):
  def __init__(self, *args):
    HardwareObject.__init__(self, *args)

  def init(self, *args):  
     sys.path.insert(0, self.getProperty("source"))
     config = __import__("config", globals(), locals(), [])
       
     cfg_file = os.path.join(self.getProperty("source"), self.getProperty("config_file")) 
     config.load(cfg_file)
     objects = config.get_context_objects("default", "default")
     self.__controller = objects["robot"]

  def __getattr__(self, attr):
     if attr.startswith("__"):
       raise AttributeError,attr
     return getattr(self.__controller, attr)


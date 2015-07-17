from Khoros import Khoros

class ID30Controller(Khoros):
  def __init__(self, *args):
     Khoros.__init__(self, *args)

  def init(self, *args):  
     Khoros.init(self)

  def set_diagfile(self, diagfile):
     self.minidiff.diagfile = diagfile

  def __getattr__(self, attr):
     if attr.startswith("__"):
       raise AttributeError,attr
     return getattr(self.minidiff, attr)


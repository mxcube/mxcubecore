
from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects

from sample_changer.CatsMaint import CatsMaint
import logging

class ALBACatsMaint(CatsMaint):

    def __init__(self, *args):
        CatsMaint.__init__(self, *args)

    def init(self):
        CatsMaint.init(self)

        # load ALBA attributes and commands from XML
        self._chnAtHome = self.getChannelObject("_chnAtHome")
        logging.getLogger("HWR").debug(" BARCODE is: %s" % self._chnBarcode.getValue())

        # channel to ask diffractometer for mounting position
        self.shifts_channel = self.getChannelObject("shifts")

    def _doResetMemory(self): 
        # Check do_PRO6_RAH first
        if self._chnAtHome.getValue() is True:
            CatsMaint._doResetMemory(self)

    def _doOperationCommand(self, cmd, pars):
        CatsMaint._doOperationCommand(self)

    def _get_shifts(self):
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.getValue()
        else:
            shifts = None
        return shifts

def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    print "Loading hardware repository from ", os.path.abspath(hwr_directory)
    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    cats = hwr.getHardwareObject("/cats")
    print cats._get_shifts()

if  __name__ == '__main__':
    test()


from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device
import logging
import PyTango

class SOLEILFlux(Device):

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):
        self.flux_channel = self.getChannelObject("flux")
    
    def getCurrentFlux(self):
        try:
            return self.flux_channel.getValue()
        except PyTango.DevFailed:
            return -1


def test():
    import os
    import time
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    flux = hwr.getHardwareObject("/flux")

    print "PX1 Flux is ",flux.getCurrentFlux()


if __name__ == '__main__':
   test()


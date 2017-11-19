import logging
import math

from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device
from DataAnalysis import DataAnalysis

class PX2DataAnalysis(DataAnalysis):

    def get_beam_size(self):
        return (0.010, 0.005)


def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    analysis = hwr.getHardwareObject("/data-analysis")
    print analysis.get_beam_size()
    print analysis.is_running()

if __name__ == '__main__':
    test()



"""
Class for reading images from Falcon camera OAV
"""
from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging
import os


class XalocCalibration(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        self.calibx = self.getChannelObject("calibx")
        self.caliby = self.getChannelObject("caliby")

        if self.calibx is not None and self.caliby is not None:
            print "Connected to calibration channels"

    def getCalibration(self):
        return [self.calibx.getValue(), self.caliby.getValue()]


def test():
    hwr = HardwareRepository.getHardwareRepository()
    hwr.connect()

    calib = hwr.getHardwareObject("/calibration")
    print "Calibration is: ", calib.getCalibration()


if __name__ == "__main__":
    test()

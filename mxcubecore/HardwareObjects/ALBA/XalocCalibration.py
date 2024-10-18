"""
Class for reading images from Falcon camera OAV
"""

from mxcubecore import HardwareRepository as HWR
from mxcubecore import BaseHardwareObjects


class XalocCalibration(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        super().__init__(name)

    def init(self):

        self.calibx = self.get_channel_object("calibx")
        self.caliby = self.get_channel_object("caliby")

        if self.calibx is not None and self.caliby is not None:
            print("Connected to calibration channels")

    def getCalibration(self):
        return [self.calibx.get_value(), self.caliby.get_value()]


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    calib = hwr.get_hardware_object("/calibration")
    print("Calibration is: ", calib.getCalibration())


if __name__ == "__main__":
    test()

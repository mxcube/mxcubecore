from mxcubecore.BaseHardwareObjects import HardwareObject
from grob import grob_control


class Grob(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        self.SampleTableMotor = grob_control.SampleTableMotor
        self.GonioMotor = grob_control.GonioMotor
        self.SampleMotor = grob_control.SampleMotor

    def init(self):
        self.controller = grob_control.init(self.grob_host, wago_host=self.wago_host)

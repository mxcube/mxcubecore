from mxcubecore.BaseHardwareObjects import Device
from grob import grob_control


class Grob(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.SampleTableMotor = grob_control.SampleTableMotor
        self.GonioMotor = grob_control.GonioMotor
        self.SampleMotor = grob_control.SampleMotor

    def init(self):
        self.controller = grob_control.init(self.grob_host, wago_host=self.wago_host)

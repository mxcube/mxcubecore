from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
import PyTango


class SOLEILFlux(HardwareObject):
    def __init__(self, name):
        super().__init__(name)

    def init(self):
        self.flux_channel = self.get_channel_object("flux")

    def get_value(self):
        try:
            return self.flux_channel.get_value()
        except PyTango.DevFailed:
            return -1


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    flux = hwr.get_hardware_object("/flux")

    print("PX1 Flux is ", flux.get_value())


if __name__ == "__main__":
    test()

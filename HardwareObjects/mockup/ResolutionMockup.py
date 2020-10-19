# from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.HardwareObjects.Resolution import Resolution


class ResolutionMockup(Resolution):
    """As Resolution is a virtual motor, no need for much code here"""

    def init(self):
        super(ResolutionMockup, self).init()

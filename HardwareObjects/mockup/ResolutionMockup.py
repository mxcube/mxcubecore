# from mx3core import HardwareRepository as HWR
from mx3core.HardwareObjects.Resolution import Resolution


class ResolutionMockup(Resolution):
    """As Resolution is a virtual motor, no need for much code here"""

    def init(self):
        super(ResolutionMockup, self).init()

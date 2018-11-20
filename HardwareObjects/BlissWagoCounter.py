import math
import logging
import operator
from HardwareRepository.BaseHardwareObjects import HardwareObject


class BlissWagoCounter(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        self.gainfactor = self.getProperty("gainfactor")
        self.wagoname = self.getProperty("wagoname")
        self.controller = self.getObjectByRole("controller")

    def getGain(self):
        counter = operator.attrgetter(self.wagoname)(self.controller)
        try:
            return counter.gain()
        except Exception:
            return -1

    def getValue(self):
        gn = self.getGain()
        if gn < 0:
            # invalid gain
            return -9999
        counter = operator.attrgetter(self.wagoname)(self.controller)
        return counter.read() * math.pow(self.gainfactor, gn)

    def getCorrectedPhysValue(self):
        return self.getValue()

    def read(self):
        return self.getValue()

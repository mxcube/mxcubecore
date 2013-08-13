#import sys; sys.stdout = sys.__stdout__;
#import pdb; pdb.set_trace()

from HardwareRepository.BaseHardwareObjects import Device


class TransmissionMockup(Device):
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels = []
        self.bits = []
        self.attno = 0
        self.getValue = self.get_value

    def init(self):
        pass

    def getAtteConfig(self):
        self.attno = len(self['atte'])

        for att_i in range(self.attno):
            obj = self['atte'][att_i]
            self.labels.append(obj.label)
            self.bits.append(obj.bits)

    def getAttState(self):
        return 0

    def getAttFactor(self):
        return 100

    def get_value(self):
        return self.getAttFactor()

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def attStateChanged(self, channelValue):
        pass

    def attFactorChanged(self, channelValue):
        pass

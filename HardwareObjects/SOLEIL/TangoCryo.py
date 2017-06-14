
from HardwareRepository import BaseHardwareObjects
import logging

class TangoCryo(BaseHardwareObjects.Device):

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        try:
            tempchan = self.getChannelObject('temperature')
            tempchan.connectSignal('update', self.temperatureChanged)
            self.temp = tempchan.getValue()
            statuschan = self.getChannelObject('state')
            statuschan.connectSignal('update', self.stateChanged)
            n2levelchan = self.getChannelObject('n2level')
            n2levelchan.connectSignal('update', self.levelChanged)
            self.n2level = n2levelchan.getValue()
            logging.getLogger().debug('%s: connected to channels', self.name())
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to channel', self.name())


    def temperatureChanged(self, value):
        #
        # emit signal
        #
        self.temp = 100 #value
        self.emit('temperatureChanged', value)


    def stateChanged(self, value):
        #
        # emit signal
        #
        self.emit('cryoStatusChanged', value)

    def levelChanged(self, value):
        #
        # emit signal
        #
        self.n2level = value
        self.emit('levelChanged', value)

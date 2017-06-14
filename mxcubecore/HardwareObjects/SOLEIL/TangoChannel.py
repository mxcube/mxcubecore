
from HardwareRepository import BaseHardwareObjects
import logging

class TangoChannel(BaseHardwareObjects.Device):

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        try:
            chobj = self.getChannelObject('channel')
            chobj.connectSignal('update', self.tangoValueChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to channel', self.name())


    def tangoValueChanged(self, value):
        #
        # emit signal
        #
        #self.emit('valueChange', value)
        self.emit('valueChanged', value)




from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging
import PyTango

class PX2Flux(BaseHardwareObjects.Device):

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        try:
            self.fluxchan = self.getChannelObject('flux')
            self.fluxchan.connectSignal('update', self.fluxChanged)
            try:
                self.flux = self.fluxchan.getValue()
            except:
                self.flux = -1
            self.statuschan = self.getChannelObject('state')
            self.statuschan.connectSignal('update', self.stateChanged)
            logging.getLogger().debug('%s: connected to channels', self.name())
        except KeyError:
            logging.getLogger().warning('%s: cannot connect to channel', self.name())
        except Exception, e:
            print "FLUX INIT, ERROR MESSAGE: %s"  % e
            logging.getLogger().info('%s: FLUX ERROR Message', self.name())            
            import traceback 
            logging.getLogger().info("flux is type: %s ", str(type(self.flux)))
            #logging.info(traceback.format_exc())            #logging.getLogger().error('%s: Message: %s', e)

    def getCurrentFlux(self):
        try:
            return self.fluxchan.getValue()
        except PyTango.DevFailed:
            return -1

    def getValue(self):
        return self.getCurrentFlux()

    def fluxChanged(self, value):
        #
        # emit signal
        #
        self.flux = value
        self.emit('fluxChanged', str("%7.1e" % value))
        self.emit('valueChanged', str("%7.1e" % self.flux))

    def stateChanged(self, value):
        #
        # emit signal
        #
        self.emit('fluxStatusChanged', value)
        self.emit('stateChanged', value)


def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    flux = hwr.getHardwareObject("/flux")
    print "PX2 Flux is ",flux.getCurrentFlux()


if __name__ == '__main__':
    test()


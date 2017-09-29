import logging
from qt import qApp
from HardwareRepository.BaseHardwareObjects import Device

class TangoLightPX1(Device):

    def __init__(self, name):
        Device.__init__(self, name)
        self.currentState = "unknown"

    def init(self):
        #self.tangoname = self.
        self.attrchan = self.getChannelObject("attributeName")
        self.attrchan.connectSignal("update", self.valueChanged)

        self.attrchan.connectSignal("connected", self._setReady)
        self.attrchan.connectSignal("disconnected", self._setReady)
        self.set_in = self.getCommandObject("set_in")
        self.set_in.connectSignal("connected", self._setReady)
        self.set_in.connectSignal("disconnected", self._setReady)
        self.set_out = self.getCommandObject("set_out")
        
        # Avoiding Beamstop + Light Arm collision.
        self.beamstop_out = self.getCommandObject("beamstop_out")
        self.beamstopState = self.getChannelObject("beamstopState")
        
        # Avoiding Colision with the Detector
        self.detdistchan = self.getChannelObject("detDistance")
        logging.getLogger("HWR").info(('TangoLightPX1. minimum Detector '
                        + 'distance for light_Arm insertion: %.1f mm') % \
                                           self.min_detector_distance)

        self._setReady()
        try:
           self.inversed = self.getProperty("inversed")
        except:
           self.inversed = False

        if self.inversed:
           self.states = ["in", "out"]
        else:
           self.states = ["out", "in"]

    def _setReady(self):
        self.setIsReady(self.attrchan.isConnected())

    def connectNotify(self, signal):
        if self.isReady():
           self.valueChanged(self.attrchan.getValue())


    def valueChanged(self, value):
        self.currentState = value

        if value:
            self.currentState = self.states[1]
        else:
            self.currentState = self.states[0]
        
        self.emit('wagoStateChanged', (self.currentState, ))
        
    def getWagoState(self):
        return self.currentState 

    def wagoIn(self):
        if str(self.beamstopState.getValue()) == 'INSERT':
            logging.getLogger("HWR").info('TangoLightPX1. Extracting BeamStop.')
            self.beamstop_out()
            while str(self.beamstopState.getValue()) != "EXTRACT":
                qApp.processEvents()
        detposition = self.detdistchan.getValue()
        logging.getLogger("HWR").info('TangoLightPX1. DetDist= %.2f mm. OK.' % detposition)
        if detposition < self.min_detector_distance:
            m1 = "Can't insert Light-arm, detector distance too close: %.1f mm. " % detposition
            m2 = "You need to set the distance to > %.1f mm." % self.min_detector_distance
            logging.getLogger("user_level_log").error("%s: " + m1+m2, self.name())
        else:
            logging.getLogger("HWR").info('TangoLightPX1. Inserting Light.')       
            self.setIn()

    def setIn(self):
        self._setReady()
        if self.isReady():
          if self.inversed:
            self.set_out()
          else:
            self.set_in()
 
    def wagoOut(self):
        logging.getLogger("HWR").info('TangoLightPX1:  in WagoOut ')
        self.setOut()

    def setOut(self):
        self._setReady()
        if self.isReady():
          if self.inversed:
            self.set_in()
          else:
            self.set_out()
           

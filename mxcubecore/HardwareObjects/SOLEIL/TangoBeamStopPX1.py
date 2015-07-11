from HardwareRepository.BaseHardwareObjects import Device
import logging
import time

class TangoBeamStopPX1(Device):

    beamstopState = {
        None: 'unknown',
        'UNKNOWN': 'unknown',
        'CLOSE': 'closed',
        'OPEN': 'opened',
        'INSERT': 'in',
        'EXTRACT': 'out',
        'MOVING': 'moving',
        'RUNNING':'moving',
        '_': 'automatic',
        'FAULT': 'fault',
        'DISABLE': 'disabled',
        'OFF': 'fault',
        'ON': 'unknown'
        }
  
    def __init__(self, name):
        Device.__init__(self, name)
        self.lastState  = None

    def init(self):

        self.setIsReady(True)

        stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
        stateChan.connectSignal("update", self.stateChanged)
    
    def stateChanged(self, state):

        logging.getLogger().debug("TangoBeamStopPX1 : stateChanged - new state = %s",state)

        if state is None or str(state)=="":
            return

        state=str(state)

        if self.lastState!=state:
            try:
              logging.getLogger().debug(" Emitting shutter state being: " + str(TangoBeamStopPX1.beamstopState[state], ))
              self.emit("stateChanged", (TangoBeamStopPX1.beamstopState[state], ))
            except KeyError:
              self.emit("stateChanged", ("unknown",))
              logging.getLogger("HWR").error("%s: unknown beamstop state %s", self.name(), state)
            self.lastState=state
    
    def moveToPosition(self, posname):
        if posname == "in":
            self.moveIn()
        elif posname == "out":
            self.moveOut()
 
    def getShutterState(self):
        return self.getState()
    def getState(self):
        logging.getLogger().debug(" Reading shutter state being: " + str(TangoBeamStopPX1.beamstopState[self.lastState], ))
        return TangoBeamStopPX1.beamstopState[self.lastState] 
        
    def isDeviceOk(self):
        logging.getLogger().debug("TangoBeamStopPX1 : isDeviceOK")       
        state = not self.getState() in ('unknown', 'moving', 'fault', 'disabled', 'error')
        return state

    def openShutter(self):
        self.moveIn()
    def moveIn(self):
        logging.getLogger().debug("TangoBeamStopPX1 : inserting beamtop")             

        lightout   = self.getCommandObject("lightout")
        lightstate = self.getCommandObject("lightstate")
        if not lightout or not lightstate:
            logging.getLogger().error("TangoBeamStopPX1 : cannot find commands lightout/lightstate in beamstop object. Check your xml configuration")
            return

        if self.isDeviceOk():
            lightout()

        t0 = time.time()
        timeout = 4.0
        while(  str( lightstate() ) != "EXTRACT" ):
            time.sleep(0.2)        
            if time.time() - t0 > timeout:
               logging.getLogger().error("TangoBeamStopPX1 : cannot get light arm out. Beamstop not inserted")
               break
        else:
            logging.getLogger().debug("TangoBeamStopPX1 : really inserting beamtop")             
            cmdOpen = self.getCommandObject("in")
            cmdOpen()
            
    def closeShutter(self):
        self.moveOut()
    def moveOut(self):
        logging.getLogger().debug("TangoBeamStopPX1 : extracting beamtop")             
        if self.isDeviceOk():
            cmdClose = self.getCommandObject("out")
            cmdClose()
        else:
            logging.getLogger("HWR").error("%s: cannot extract beamstop (%s)", self.name(), self.getState())

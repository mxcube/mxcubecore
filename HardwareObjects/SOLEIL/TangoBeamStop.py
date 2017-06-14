from HardwareRepository.BaseHardwareObjects import Device
from PyTango import DeviceProxy
import logging
import time

class TangoBeamStop(Device):
    beamstopState = {
        None: 'unknown',
        'UNKNOWN': 'unknown',
        'CLOSE': 'closed',
        'OPEN': 'opened',
        'INSERT': 'opened',
        'EXTRACT': 'closed',
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

        self.shutterStateValue = 0
        self.lastState = None
        #self.PSSdevice = None

    def init(self):
        #stateChan = self.addChannel({ 'type': 'tango', 'name': 'state', 'polling':500 }, "State")
        #self.addCommand({'type': 'tango', 'name': 'open' }, "Open")
        #self.addCommand({'type': 'tango', 'name': 'close' }, "Close")
        self.setIsReady(True)
        # Connect to device PSS "tangoname2" in the xml file 
        #try :    
        #    self.PSSdevice = SimpleDevice(self.getProperty("tangoname2"), verbose=False)
        #except :    
#       #     self.errorDeviceInstance(self.getProperty("tangoname2"))
        #     logging.getLogger("HWR").info("%s: unknown pss device name", self.getProperty("tangoname2"))
        try :    
            self.LightArm = DeviceProxy(self.getProperty("tangoname2"))
        except :    
             logging.getLogger("HWR").info("%s: unknown lightarm device name", self.getProperty("tangoname2"))
        stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
        stateChan.connectSignal("update", self.stateChanged)
    
    def stateChanged(self, state):
        logging.getLogger().debug("TangoBeamStop : stateChanged - new state = %s",state)
        if state is None or str(state)=="":
            return
        state=str(state)
        if self.lastState!=state:
            try:
              self.emit("shutterStateChanged", (TangoBeamStop.beamstopState[state], ))
            except KeyError:
              self.emit("shutterStateChanged", ("unknown",))
              logging.getLogger("HWR").error("%s: unknown shutter state %s", self.name(), state)
            self.lastState=state
    
    def getShutterState(self):
        #logging.getLogger().debug("TangoBeamStop : passe dans getShutterState.")
        #if self.isPssOk:
        return TangoBeamStop.beamstopState[self.lastState] 
        
    def isShutterOk(self):
        logging.getLogger().debug("TangoBeamStop : isSutterOK")       
        stateShutter = not self.getShutterState() in ('unknown', 'moving', 'fault', 'disabled', 'error')
        return stateShutter

    #def isPssOk(self):
    #    statePSS = True
    #    if self.PSSdevice:       
    #        statePSS = self.PSSdevice.pssStatusEH == 1
    #        if statePSS == False :
    #              logging.getLogger("HWR").error("%s: experimental hutch search is not finished",self.name())
    #    return statePSS


    def openShutter(self):
        logging.getLogger().debug("TangoBeamStop : passe dans openShutter")             

#        if self.isReady() and self.isShutterOk() and self.isPssOk():
        #if self.isShutterOk() and self.isPssOk():
         #   logging.getLogger().debug("TangoBeamStop : passe dans openShutter 2")             
        if self.isShutterOk():
            if str(self.LightArm.State()) == "INSERT":
                self.LightArm.Extract()
                time.sleep(2)        
            cmdOpen = self.getCommandObject("open")
            #logging.getLogger().debug("TangoBeamStop : passe dans openShutter 3")             
            cmdOpen()
            #logging.getLogger().debug("TangoBeamStop : passe dans openShutter : shutter open")             
        #else:
        #    logging.getLogger("HWR").error("%s: cannot open shutter (%s)", self.name(), self.getShutterState())
            

    def closeShutter(self):
#        if self.isReady() and self.isShutterOk():
        logging.getLogger().debug("TangoBeamStop : passe dans closeShutter")             
        if self.isShutterOk():
            #if self.LightArm.State == "INSERT":
            #    self.LightArm.Extract()
            #    time.sleep(2)
            cmdClose = self.getCommandObject("close")
            cmdClose()
        else:
            logging.getLogger("HWR").error("%s: cannot close shutter (%s)", self.name(), self.getShutterState())

import logging
import time

from HardwareRepository.BaseHardwareObjects import Device
from PyTango import DeviceProxy

class TangolightPneu(Device):
    states = {
      0:   "out",
      1:   "in",
    }

    READ_CMD, READ_OUT = (0,1)
    
    def __init__(self, name):
        Device.__init__(self, name)

        #self.wagoidin  = None
        #self.wagoidout = None
        self.wagokyin  = None
        self.wagokyout = None
        #self.logic     = 1
        #self.readmode  = WagoPneu.READ_OUT
        self.wagoState = "unknown"
        self.__oldValue = None
        self.device = None
        self.hutch = None
        self.lastState = None
        self.simulation=False

    def init(self):
        try :    
            self.device = DeviceProxy(self.getProperty("tangoname") )
        except :    
            logging.getLogger("HWR").error("%s: unknown pss device name", self.getProperty("tangoname"))

        try :    
            self.device_beamstop = DeviceProxy(self.getProperty("tangoname2") )
        except :    
            logging.getLogger("HWR").error("%s: unknown  device name", self.getProperty("tangoname2"))

        try :    
            self.device_detdist = DeviceProxy(self.getProperty("tangoname3"))
        except :    
            logging.getLogger("HWR").error("%s: unknown  device name", self.getProperty("tangoname3"))

        if self.device and self.device_beamstop and self.device_detdist:
            self.setIsReady(True)
    
    def valueChanged(self,value):
        state = self.getWagoState()
        self.emit('wagoStateChanged', (state, ))
            
    def getTangoState(self) :
        return str( self.device.State() )
         
    def getWagoState(self):
        value = int(self.device.isInserted)
        
        if value in TangolightPneu.states:
             self.wagoState = TangolightPneu.states[value]
        else:
             self.wagoState = "unknown"
        logging.getLogger("HWR").info("%s: TangolightPneu.getWagoState, %s", self.name(), self.wagoState)
       
        return self.wagoState 


    def wagoIn(self):
        logging.getLogger("HWR").info("%s: TangolightPneu.wagoIn", self.name())
        if self.isReady():
            if self.simulation==True:
                self.device.isInserted=True
            else:
                # PL. 2010.01.22: Les etats du DS BPS ne sont pas mis a jour pour l'instant.
                # Il n'y a pas de butees pour cela. On force donc l'extraction du BStop.
                if str( self.device_beamstop.State()) != "EXTRACT":
                    self.device_beamstop.Extract()
                while str( self.device_beamstop.State() ) != "EXTRACT":
                    qApp.processEvents()
                #qApp.processEvents()
                detposition = self.device_detdist.position
                min_detposition = 269.5
                if detposition < min_detposition:
                    msg = "Can't insert Light-arm, detector distance too close:"
                    msg += "%.1f  You need to set the distance to > %.1f mm." %\
                                 (detposition, min_detposition)
                    logging.getLogger("HWR").error("%s: " + msg, self.name())
                    return
                time.sleep(0.2)
                self.device.Insert()
                timeout = 0
                while self.getTangoState() != "INSERT":
                    time.sleep(0.2)
                    timeout += 0.2
                    if timeout >= 4.0 :
                        break
                if self.getTangoState() != "INSERT":      
                    logging.getLogger("HWR").error("%s: LIGHT ARM NOT CORRECTLY INSERTED", self.name())

            
    def wagoOut(self):
        logging.getLogger("HWR").info("%s: TangolightPneu.wagoOut", self.name())
        if self.isReady():
            if self.simulation==True:
                self.device.isInserted=False
            else:
                self.device.Extract()
                pass

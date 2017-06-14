# -*- coding: utf-8 -*-
import logging
import time
from HardwareRepository.BaseHardwareObjects import Device
from PyTango import DeviceProxy
#from SimpleDevice import SimpleDevice
'''Complex means we are not using SimpleDevice'''

class TangoPssComplex(Device):
    states = {
      0:   "not ready",
      1:   "ready",
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
        self.detector_dist = None
        self.beamstop = None
        self.hutch = None
        self.lastState = None

    def init(self):
        #logging.getLogger("HWR").info("%s: TangoPss.init", self.name())
        try:
            self.device = DeviceProxy(self.getProperty("tangoname")) #, verbose=False)
            #self.device.timeout = 5000
            #self.detector_dist = SimpleDevice(self.getProperty("tangoname_detector_dist"), verbose=False)
            #self.beamstop = SimpleDevice(self.getProperty("tangoname_beamstop"), verbose=False)
            #self.guillot = SimpleDevice(self.getProperty("tangoname_guillot"), verbose=False)
        except:
#            self.errorDeviceInstance(self.getProperty("tangoname2"))
            logging.getLogger("HWR").error("%s: unknown pss device name", self.getProperty("tangoname"))
#        stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
#        stateChan.connectSignal("update", self.stateChanged) 
        #logging.getLogger("HWR").info("%s: TangoPss.init devicename :%s",
        #                                        self.name(), self.device)
        if self.getProperty("hutch") not in ("optical", "experimental"):
            logging.getLogger("HWR").error("TangoPss.init Hutch property %s is not correct",self.getProperty("hutch"))
        else :
            self.hutch  = self.getProperty("hutch")
            if self.hutch == "optical" :
                stateChan = self.addChannel({ 'type': 'tango', 'name': 'pssStatusOH', 'polling':1000 }, "pssStatusOH")
            else :
                stateChan = self.addChannel({ 'type': 'tango', 'name': 'prmObt', 'polling':1000 }, "prmObt")
            stateChan.connectSignal("update", self.valueChanged)
        if self.device:
            self.setIsReady(True)
    
    def valueChanged(self,value):
        logging.getLogger("HWR").info("%s: TangoPss.valueChanged, %s", self.name(), value)
        state = self.getWagoState()
        self.emit('wagoStateChanged', (state, ))
            
    
    def getWagoState(self):
        if self.hutch == "optical" :
            value = int(self.device.pssStatusOH)
        elif self.hutch == "experimental" :
            value = int(self.device.prmObt)
        else :
            self.wagoState = "unknown"
            return self.wagoState
        print "value PSS :" , value
        if value != self.__oldValue:
            self.__oldValue = value
        if value in TangoPssComplex.states:
             self.wagoState = TangoPssComplex.states[value]
        else:
             self.wagoState = "unknown"
        #print "wagoState :" , self.wagoState
        return self.wagoState 


    def wagoIn(self):
        logging.getLogger("HWR").info("%s: TangoPss.wagoIn", self.name())
        if self.isReady():
            #self.device.DevWriteDigi([ self.wagokyin, 0, 1 ]) #executeCommand('DevWriteDigi(%s)' % str(self.argin))
            pass

            
    def wagoOut(self):
        logging.getLogger("HWR").info("%s: TangoPss.wagoOut", self.name())
        if self.isReady():
            #self.device.DevWriteDigi([ self.wagokyin, 0, 0 ]) #executeCommand('DevWriteDigi(%s)' % str(self.argin))
            pass

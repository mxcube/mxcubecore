# -*- coding: utf-8 -*-
#from SimpleDevice2c import SimpleDevice
from PyTango import DeviceProxy
import logging

from HardwareRepository.BaseHardwareObjects import Device

class AttenuatorsPX2(Device):
    stateAttenuator = {'ALARM' : 0,'EXTRACT' : 1,'INSERT' : 1,'UNKNOWN' : 3, 'ALARM' : 'error','OFF' : 'error', 'RUNNING' : 'moving','MOVING' : 'moving', 'STANDBY' : 'ready', 'UNKNOWN': 'changed', 'EXTRACT': 'outlimits'}
    
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels  = []
        self.bits    = []
        self.attno   = 0
        self.deviceOk = True
        self.NumToLabel = {}
        

    def init(self):
        #cmdToggle = self.getCommandObject('toggle')
        #cmdToggle.connectSignal('connected', self.connected)
        #cmdToggle.connectSignal('disconnected', self.disconnected)
        
        # Connect to device Attenuator defined "tangoname" in the xml file 
        try :
            #self.Attenuatordevice = SimpleDevice(self.getProperty("tangoname"), verbose=False)
            self.Attenuatordevice = DeviceProxy(self.getProperty("tangoname"))
            self.Attenuatordevice.waitMoves = False
            self.Attenuatordevice.timeout = 5000

        except :
            self.errorDeviceInstance(self.getProperty("tangoname"))

        if self.deviceOk:
            #self.connected()
            #self.chanAttState = self.getChannelObject('State')
            #print "self.chanAttState : ", self.chanAttState
            #self.chanAttState.connectSignal('update', self.attStateChanged)
            ##self.chanAttFactor = self.getChannelObject('appliedTransmission')
            ##self.chanAttFactor = self.getChannelObject('computedTransmission')
            ##self.chanAttFactor.connectSignal('update', self.attFactorChanged)
            
            ##self.chanAttToggle = self.getChannelObject('filtersCombination')
            ##self.chanAttToggle.connectSignal('update', self.attToggleChanged)
            
            #self.getAtteConfig()
            
            self.connected()
            self.chanAttState = self.getChannelObject('State')
            print "self.chanAttState : ", self.chanAttState
            self.chanAttState.connectSignal('update', self.attStateChanged)
            #self.chanAttFactor = self.getChannelObject('appliedTransmission')
            
            self.chanAttFactor = self.getChannelObject('Status')
            self.chanAttFactor.connectSignal('update', self.attFactorChanged)
            
            self.chanAttToggle = self.getChannelObject('State')
            self.chanAttToggle.connectSignal('update', self.attToggleChanged)
            
            self.getAtteConfig()
            
        logging.getLogger().debug("AttenuatorsPX2: self.labels, self.bits, self.attno, %s, %s, %s" %( self.labels, self.bits, self.attno))
        
    def getAtteConfig(self):
        pass

    def getAtteConfig_OLD(self):
        logging.getLogger().debug("HOS Attenuator: passe dans getAtteConfig")
        self.attno = len( self['atte'] )

        for att_i in range( self.attno ):
           obj = self['atte'][att_i]
           self.labels.append( obj.label )
           self.bits.append( obj.bits )
        self.NumToLabel = dict([(int(l.split()[0]), l) for l in self.labels])
        
    def getAttState(self):
        logging.getLogger().debug("HOS Attenuator: passe dans getAttState")
        logging.getLogger().debug("Attenuator state read from the device %s",self.Attenuatordevice.State().name)
        try:
            #print "HEYO", self.Attenuatordevice.StatefiltersCombination
            print self.Attenuatordevice.Status()
            value= AttenuatorsPX2.stateAttenuator[self.Attenuatordevice.State().name]
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a integer value', str(self.name()))
            value=None
        return value

    def getAttFactor(self):
        logging.getLogger().debug("HOS Attenuator: passe dans getAttFactor")
        print 'self.Attenuatordevice.Status()', self.Attenuatordevice.Status() 
        try:
            #value = float(self.Attenuatordevice.appliedTransmission)
            status = self.Attenuatordevice.Status()
            status = status[:status.index(':')]
            print 'status', status
            value = status #self.Attenuatordevice.Status() #1. #float(self.Attenuatordevice.computedTransmission)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
            value=None
        return value

    def connected(self):
        self.setIsReady(True)
 
    def disconnected(self):
        self.setIsReady(False)

    def attStateChanged(self, channelValue):
        logging.getLogger("HWR").debug("%s: AttenuatorsPX2.attStateChanged: %s", self.name(), channelValue)
        self.emit('attStateChanged', (AttenuatorsPX2.stateAttenuator[str(channelValue)], ))

    def attFactorChanged(self, channelValue):
        print 'attFactorChanged', channelValue
        print 'self.Attenuatordevice.Status()', self.Attenuatordevice.Status()
        try:
            status = self.Attenuatordevice.Status()
            status = status[:status.index(':')]
            print 'status', status
            value = status
            #value = float(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
        else:
            logging.getLogger("HWR").info('%s: AttenuatorsPX2, received value on channel', str(self.name()))
            self.emit('attFactorChanged', (value, )) 
    
    def attToggleChanged(self, channelValue):
#        print "Dans attToggleChanged  channelValue = %s" %channelValue
        logging.getLogger().debug("HOS Attenuator: passe dans attToggleChanged")
        try:
            value = int(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
        else:
            self.emit('toggleFilter', (value, )) 
            
    def setTransmission(self, value) :
        logging.getLogger("HWR").debug("%s: AttenuatorsPX2.setTransmission: %s", self.name(), value)
        print value
        self.Attenuatordevice.write_attribute(self.NumToLabel[value], True) #.computedAttenuation = 1.0/(value/100.0)
        #try:
            #self.Attenuatordevice.write_attribute(value, True) #.computedAttenuation = 1.0/(value/100.0)
        #except:
            #logging.getLogger("HWR").error('%s: received value on channel is not valid', str(self.name()))
            #value=None
        return value
        
    def toggle(self, value) :
        print "Toggle value = %s" %value
        logging.getLogger().debug("HOS Attenuator: passe dans toggle")
        self.Attenuatordevice.write_attribute(value, True)
        
#        old_value = self.Attenuatordevice.filtersCombination       
#        try:
#            self.Attenuatordevice.filtersCombination = old_value "sys/database/dbds1")+ (2**(value-1))
#        except:
#            logging.getLogger("HWR").error('%s: the filter doesn\'t exist', str(self.name()))
#            value=None
        return value
                          
            
    def errorDeviceInstance(self,device) :
        #db = SimpleDevice("sys/database/dbds1")
        db = DeviceProxy("sys/database/dbds1")
        logging.getLogger().error("Check Instance of Device server %s" % db.DbGetDeviceInfo(device)[1][3])
        self.sDisconnected()
  

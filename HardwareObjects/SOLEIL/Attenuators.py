import logging
from PyTango import DeviceProxy

from HardwareRepository.BaseHardwareObjects import Device

class Attenuators(Device):
    stateAttenuator = {'ALARM' : 0,'EXTRACT' : 1,'INSERT' : 1,'UNKNOWN' : 3}

    def __init__(self, name):
        Device.__init__(self, name)

        self.labels  = []
        self.bits    = []
        self.attno   = 0
        self.deviceOk = True
        

    def init(self):
#         cmdToggle = self.getCommandObject('toggle')
#         cmdToggle.connectSignal('connected', self.connected)
#         cmdToggle.connectSignal('disconnected', self.disconnected)
        
        # Connect to device Attenuator defined "tangoname" in the xml file 
        try :
            self.Attenuatordevice = DeviceProxy(self.getProperty("tangoname"))
        except :
            self.errorDeviceInstance(self.getProperty("tangoname"))

        if self.deviceOk:
            self.connected()
            self.chanAttState = self.getChannelObject('State')
            self.chanAttState.connectSignal('update', self.attStateChanged)
            #self.chanAttFactor = self.getChannelObject('appliedTransmission')
            self.chanAttFactor = self.getChannelObject('computedTransmission')
            self.chanAttFactor.connectSignal('update', self.attFactorChanged)
            
            #self.chanAttToggle = self.getChannelObject('filtersCombination')
            #self.chanAttToggle.connectSignal('update', self.attToggleChanged)
            
            self.getAtteConfig()

    
    def getAtteConfig(self):
        #logging.getLogger().debug("HOS Attenuator: passe dans getAtteConfig")
        self.attno = len( self['atte'] )

        for att_i in range( self.attno ):
           obj = self['atte'][att_i]
           self.labels.append( obj.label )
           self.bits.append( obj.bits )


    def getAttState(self):
        #logging.getLogger().debug("HOS Attenuator: passe dans getAttState")
#        logging.getLogger().debug("Attenuator state read from the device %s",self.Attenuatordevice.State)
        try:
            print "HEYO", self.Attenuatordevice.State
            value= Attenuators.stateAttenuator[str( self.Attenuatordevice.State() )]
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a integer value', str(self.name()))
            value=None
        return value


    def getAttFactor(self):
#        logging.getLogger().debug("HOS Attenuator: passe dans getAttFactor")
        
        try:
            #value = float(self.Attenuatordevice.appliedTransmission)
            print "HEY:", self.Attenuatordevice.computedTransmission
            value = float(self.Attenuatordevice.computedTransmission)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
            value=None
        return value


    def connected(self):
        self.setIsReady(True)
 
        
    def disconnected(self):
        self.setIsReady(False)


    def attStateChanged(self, channelValue):
#        logging.getLogger("HWR").debug("%s: Attenuators.attStateChanged: %s", self.name(), channelValue)
        self.emit('attStateChanged', (Attenuators.stateAttenuator[str(channelValue)], ))


    def attFactorChanged(self, channelValue):
        try:
            value = float(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
        else:
            self.emit('attFactorChanged', (value, )) 
    
    def attToggleChanged(self, channelValue):
        try:
            value = int(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
        else:
            self.emit('toggleFilter', (value, )) 
            
    def setTransmission(self,value) :
        logging.getLogger("HWR").debug("%s: Attenuators.setTransmission: %s", self.name(), value)
        
        try:
            self.Attenuatordevice.computedAttenuation = 1.0/(value/100.0)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not valid', str(self.name()))
            value=None
        return value
        
    def toggle(self,value) :
        logging.getLogger().debug("HOS Attenuator: passe dans toggle")
#        old_value = self.Attenuatordevice.filtersCombination       
#        try:
#            self.Attenuatordevice.filtersCombination = old_value + (2**(value-1))
#        except:
#            logging.getLogger("HWR").error('%s: the filter doesn\'t exist', str(self.name()))
#            value=None
        return value
                          
            
    def errorDeviceInstance(self,device) :
        db = SimpleDevice("sys/database/dbds1")
        logging.getLogger().error("Check Instance of Device server %s" % db.DbGetDeviceInfo(device)[1][3])
        self.sDisconnected()
  

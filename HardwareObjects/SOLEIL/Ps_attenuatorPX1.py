import logging
import math


from HardwareRepository.BaseHardwareObjects import Device
from PyTango import DeviceProxy

class Ps_attenuatorPX1(Device):
    stateAttenuator = {'ALARM' : 'error','OFF' : 'error', 'RUNNING' : 'moving','MOVING' : 'moving', 'STANDBY' : 'ready', 'UNKNOWN': 'changed', 'EXTRACT': 'outlimits'}

    def __init__(self, name):
        Device.__init__(self, name)

        self.labels  = []
        self.attno   = 0
        self.deviceOk = True
        

    def init(self):
#         cmdToggle = self.getCommandObject('toggle')
#         cmdToggle.connectSignal('connected', self.connected)
#         cmdToggle.connectSignal('disconnected', self.disconnected)
        
        # Connect to device FP_Parser defined "tangoname" in the xml file 
        try :
            self.Attenuatordevice = DeviceProxy(self.getProperty("tangoname"))
        except :
            self.errorDeviceInstance(self.getProperty("tangoname"))
                       
        if self.deviceOk:
            self.connected()

            self.chanAttState = self.getChannelObject('State')
            self.chanAttState.connectSignal('update', self.attStateChanged)

            self.chanAttFactor = self.getChannelObject('TrueTrans_FP')
            self.chanAttFactor.connectSignal('update', self.attFactorChanged)
                         

    def getAttState(self):
        logging.getLogger().info("HOS Attenuator: passe dans getAttState")
        try:
            value= Ps_attenuatorPX1.stateAttenuator[self.Attenuatordevice.State().name]
            print 'State Ps_Attenuator : ' , Ps_attenuatorPX1.stateAttenuator[self.Attenuatordevice.State().name]
            logging.getLogger().debug("Attenuator state read from the device %s",value)
        except:
            logging.getLogger("HWR").error('%s getAttState : received value on channel is not a integer value', str(self.name()))
            value=None
        return value
    
    def attStateChanged(self, channelValue):
        logging.getLogger().info("HOS Attenuator: passe dans attStateChanged")
        value = self.getAttState()
        self.emit('attStateChanged', (value, ))


    def getAttFactor(self):
        logging.getLogger().info("HOS Attenuator: passe dans getAttFactor")
        
        try:
#            if self.Attenuatordevice.TrueTrans_FP  <= 100.0 :
#                value = float(self.Attenuatordevice.TrueTrans_FP)
#            else :    
#                value = float(self.Attenuatordevice.T)
            value = float(self.Attenuatordevice.TrueTrans_FP)
        except:
            logging.getLogger("HWR").error('%s getAttFactor : received value on channel is not a float value', str(self.name()))
            value=None
        return value


    def connected(self):
        self.setIsReady(True)
 
        
    def disconnected(self):
        self.setIsReady(False)




    def attFactorChanged(self, channelValue):
        try:
            print "Dans attFactorChanged channelValue = %f"  %channelValue
#  	    value = float(channelValue)
            value = self.getAttFactor()
        except:
            logging.getLogger("HWR").error('%s attFactorChanged : received value on channel is not a float value', str(self.name()))
        else:
            self.emit('attFactorChanged', (value, )) 
    
    def attToggleChanged(self, channelValue):
#        print "Dans attToggleChanged  channelValue = %s" %channelValue
#        logging.getLogger().debug("HOS Attenuator: passe dans attToggleChanged")
        try:
            value = int(channelValue)
        except:
            logging.getLogger("HWR").error('%s attToggleChanged : received value on channel is not a float value', str(self.name()))
        else:
            self.emit('toggleFilter', (value, )) 
            
    def setTransmission(self,value) :
        logging.getLogger().debug("HOS Attenuator: passe dans setTransmission")       
        try:
            self.Attenuatordevice.TrueTrans_FP = value
        except:
            logging.getLogger("HWR").error('%s set Transmission : received value on channel is not valid', str(self.name()))
            value=None
        return value
        
    def toggle(self,value) :
        logging.getLogger().debug("HOS Attenuator: passe dans toggle")
        return value
                          
            
    def errorDeviceInstance(self,device) :
        db = DeviceProxy("sys/database/dbds1")
        logging.getLogger().error("Check Instance of Device server %s" % db.DbGetDeviceInfo(device)[1][3])
        self.sDisconnected()



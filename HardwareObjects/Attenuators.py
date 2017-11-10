import gevent
import logging
from HardwareRepository.BaseHardwareObjects import Device

class Attenuators(Device):
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels  = []
        self.bits    = []
        self.attno   = 0
        self.getValue = self.get_value
        self.att_value = None 
        self.att_state = None
        self.att_limits = None   

        self.chan_att_value = None
        self.chan_att_state = None 
        self.chan_att_limits = None

    def init(self):
        """
        Descript. :
        """
        self.chan_att_value = self.getChannelObject('chanAttValue')
        self.chan_att_value.connectSignal('update', self.att_value_changed)
        self.chan_att_state = self.getChannelObject('chanAttState')
        self.chan_att_state.connectSignal('update', self.att_state_changed)
        self.chan_att_limits = self.getChannelObject('chanAttLimits')
        self.chan_att_limits.connectSignal('update', self.att_limits_changed)
        
        self.connected()     
        try:
            self.getAtteConfig()
        except:
            pass
    
    def getAtteConfig(self):
        """
        Descript. :
        """
        self.attno = len( self['atte'] )
        for att_i in range( self.attno ):
           obj = self['atte'][att_i]
           self.labels.append( obj.label )
           self.bits.append( obj.bits )

    def getAttState(self):
        """
        Descript. :
        """
        try:
            value= self.chan_att_state.getValue()
        except:
            value=None
        return value

    def getAttFactor(self):
        """
        Descript. :
        """
        try:
            self.att_value = float(self.chan_att_value.getValue())
        except:
            self.att_value = None
        return self.att_value

    def get_value(self):
        """
        Descript. :
        """
        return self.getAttFactor()

    def connected(self):
        """
        Descript. :
        """
        self.setIsReady(True)
        
    def disconnected(self):
        """
        Descript. :
        """
        self.setIsReady(False)

    def att_state_changed(self, state):
        """
        Descript. :
        """
        self.att_state = state
        self.emit('attStateChanged', (self.att_state, ))

    def att_value_changed(self, value):
        """
        Descript. :
        """
        try:
  	    self.att_value = float(value)
        except:
            pass
        else:
            self.emit('attFactorChanged', (self.att_value, )) 

    def att_limits_changed(self, value):
        """
        Descript. :
        """
        try:
            self.att_limits = list(value)
        except:
            pass
        else:
            self.emit('attLimitsChanged', (self.att_limits, ))

    def get_transmission_limits(self):
        """
        Descript. :
        """
        if self.chan_att_limits is not None:
            self.att_limits = self.chan_att_limits.getValue()
        return self.att_limits    
  	      
    def is_in(self, attenuator_index):
        """
        Descript. :
        """
        curr_bits = self.getAttState()
        val = self.bits[attenuator_index]
        return bool(val & curr_bits)

    def transmissionValueGet(self):
        """
        Descript. :
        """
        return self.getAttFactor()

    def setTransmission(self, value, timeout=None):
        """
        Descript. :
        """
        self.chan_att_value.setValue(value)
        if timeout is not None:
            with gevent.Timeout(timeout, Exception("Timeout waiting for state ready")):
                while self.att_state != "ready":
                      gevent.sleep(0.1)

    def update_values(self):
        self.att_value = self.getAttFactor()
        self.emit('attStateChanged', (self.att_state, ))
        self.emit('attFactorChanged', (self.att_value, ))
        self.emit('attLimitsChanged', (self.att_limits, ))

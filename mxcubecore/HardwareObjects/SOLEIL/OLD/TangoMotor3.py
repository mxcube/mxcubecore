# -*- coding: utf-8 -*-
import logging
from HardwareRepository.BaseHardwareObjects import Device
#from SimpleDevice import SimpleDevice
from PyTango import DeviceProxy


#from qt import *

class TangoMotor3(Device):
    
    stateDict = {
         "UNKNOWN": 0,
         "ALARM":   1,
         "FAULT":   1,
         "STANDBY": 2,
         "RUNNING": 4,
         "MOVING":  4,
         "ON": 2,
         '2':         2}


    def __init__(self, name):
        Device.__init__(self, name)
        self.GUIstep = 0.1

    def _init(self):
        
        self.MOVESTARTED = 0
        self.NOTINITIALIZED = 0
        self.UNUSABLE = 0
        self.READY = 2
        self.MOVING = 4
        self.ONLIMITS = 1

        self.device = DeviceProxy(self.getProperty("tangoname"))
        self.device.waitMoves = False
        self.setIsReady(True)
        print "TangoMotor._init of device %s" % self.device.name

        self.positionChan = self.getChannelObject("attributeName") # utile seulement si statechan n'est pas defini dans le code
        self.positionChan.connectSignal("update", self.positionChanged) 

        self.stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
        self.stateChan.connectSignal("update", self.stateChanged) 
#         
#        logging.getLogger("HWR").info("%s: TangoMotor._init, %s", self.name(), '')
        

    def positionChanged(self, value):
        try:
            logging.getLogger("HWR").info("%s: TangoMotor.positionChanged: %.3f", self.name(), value)
        except:
            logging.getLogger("HWR").error("%s: TangoMotor not responding, %s", self.name(), '')
        
        self.emit('positionChanged', (value,))
    
    def isReady(self):
        #logging.getLogger("HWR").info("%s: TangoMotor.isReady", self.name())
        return self.motorState() == TangoMotor3.stateDict["STANDBY"]
        
        
    def connectNotify(self, signal):
        #logging.getLogger("HWR").info("%s: TangoMotor.connectNotify, : %s", \
        #                                                  self.name(), signal)
        if signal == 'hardwareObjectName,stateChanged':
            self.motorStateChanged(self.motorState())
        elif signal == 'limitsChanged':
            self.motorLimitsChanged()
            #print "Not implemented yet."
            
        elif signal == 'positionChanged':
            self.motorPositionChanged(self.positionChan.getValue())
            
        self.setIsReady(True)
    
    def motorState(self):
        return self.getState()
    
    def stateChanged(self, state):
        logging.getLogger("HWR").info("State Changed, %s / %s" % (self.name(), str(state)))
        self.motorStateChanged(state)
      
    def motorStateChanged(self, state):
        logging.getLogger("HWR").info("%s: TangoMotor.motorStateChanged, %s", self.name(), state)
        #self.setIsReady(state == 'STANDBY')
        self.setIsReady(True)
        print "motorStateChanged", str(state),self.motorState()
        self.emit('stateChanged', (self.motorState(), ))
        
    def getState(self):
        state = str(self.device.State())
        #logging.getLogger("HWR").info("%s: TangoMotor.getState, %s", self.name(), state)
        #return self.motorState()
        return TangoMotor3.stateDict[ state ]
    
    def getLimits(self):
        #limits = self.device.getLimits(str(self.positionChan.attributeName))
        try:
           atprops = self.device.attribute_query(str(self.positionChan.attributeName))
           limits = map(float, [atprops.min_value, atprops.max_value])
           logging.getLogger("HWR").info("TangoMotor3 getLimits returning %.4f %.4f" % (limits[0], limits[1]))
           return limits
        except IndexError:
           logging.getLogger("HWR").info("TangoMotor3 cannot getLimits returning -1,1" )
           return (-1,1)
        
    def motorLimitsChanged(self):
        #self.emit('limitsChanged', (self.getLimits(), ))
        #logging.getLogger("HWR").info("%s: TangoMotor.limitsChanged", self.name())
        self.emit('limitsChanged', (self.getLimits(), )) 
                      
    def motorMoveDone(self, channelValue):
       #SpecMotorA.motorMoveDone(self, channelValue)
       #logging.getLogger("HWR").info("TangoMotor.motorMoveDone")
       if str(self.device.State()) == 'STANDBY':
           
          #self.emit('moveDone', (self.specversion, self.specname, ))
          self.emit('moveDone', ("EH3","toto" ))
          
    def motorPositionChanged(self, absolutePosition):
        self.motorStateChanged(self.device.State())
        self.emit('positionChanged', (absolutePosition, ))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        return '0' #NO ('1' means YES)
    
    def getPosition(self):
        pos = self.positionChan.getValue()
        #logging.getLogger("HWR").info("%s: TangoMotor.getPosition, pos = %.3f", self.name(), pos)
        return pos
    
    def syncMove(self, position):
        #print 'about to start moving', self.motorState
        import time; t0=time.time()
        prev_position = self.getPosition()
        self.positionChan.value = position

        print 'move started from %s to %s, state is %s' % (prev_position, position, self.getState())
        
        while self.getState() == "RUNNING" or self.getState() == "MOVING": # or str(self.device.State()) == SpecMotor.MOVESTARTED:
            #print 'processing events...', self.motorState
            qApp.processEvents(100)

        print 'move done (%s s), state is %s' % (time.time()-t0,  str(self.device.State()))
        

    def syncMoveRelative(self, position):
        old_pos = self.positionChan.getValue()
        self.positionChan.value = old_pos + position
        #self.moveRelahardwareObjectName,tive(position)

        while self.getState() == "RUNNING" or self.getState() == "MOVING":
            qApp.processEvents(100)
        
    def moveRelative(self, position):
        old_pos = self.positionChan.getValue()
        self.positionChan.value = old_pos + position
        #self.moveRelahardwareObjectName,tive(position)
        self.syncMove(self.positionChan.value)
            
    def getMotorMnemonic(self):
        return self.specName

    def move(self, absolutePosition):
        """Move the motor to the required position

        Arguments:
        absolutePosition -- position to move to
        """
        if type(absolutePosition) != float and type(absolutePosition) != int:
            logging.getLogger("TangoClient").error("Cannot move %s: position '%s' is not a number", self.device.name, absolutePosition)
            
        #self.__changeMotorState(MOVESTARTED)

        #c = self.connection.getChannel(self.chanNamePrefix % 'start_one')
        logging.getLogger("HWR").info("TangoMotor.move to absolute position: %.3f" % absolutePosition)
        self.positionChan.value = absolutePosition
        print self.positionChan.value
        nom_attribut=self.positionChan.attributeName
        setattr(self.device,nom_attribut,absolutePosition)
        self.motorPositionChanged(absolutePosition)

    def stop(self):
        logging.getLogger("HWR").info("TangoMotor.stop")
        self.device.Stop()

    def isSpecConnected(self):
        logging.getLogger().debug("%s: TangoMotor.isSpecConnected()" % self.name())
        return TruehardwareObjectName,
    
    

    
       

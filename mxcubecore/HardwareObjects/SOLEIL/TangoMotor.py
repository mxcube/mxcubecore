# -*- coding: utf-8 -*-
import logging
import time
from HardwareRepository.BaseHardwareObjects import Device
#from SimpleDevice import SimpleDevice
from PyTango import DeviceProxy

from qt import *

class TangoMotor(Device):
    
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
        self.ONLIMIT = 1

        self.device = DeviceProxy(self.getProperty("tangoname")) #, verbose=False)
        self.device.timeout = 6000 # Setting timeout to 6 sec
        self.device.waitMoves = False
        logging.getLogger("HWR").info("TangoMotor._init of device %s" % self.device.name)
        self.setIsReady(True)
        print "TangoMotor._init of device %s" % self.device.name
        positionChan = self.getChannelObject("position") # utile seulement si statechan n'est pas defini dans le code
        positionChan.connectSignal("update", self.positionChanged) 
        stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
        stateChan.connectSignal("update", self.motorStateChanged) 
        
        #logging.getLogger("HWR").info("%s: TangoMotor._init, %s", self.name(), '')
        

    def positionChanged(self, value):
        try:
            logging.getLogger("HWR").info("%s: TangoMotor.positionChanged: %.3f", self.name(), value)
        except:
            logging.getLogger("HWR").error("%s: TangoMotor not responding, %s", self.name(), '')
        
        self.emit('positionChanged', (value,))
    
    def isReady(self):
        #logging.getLogger("HWR").info("%s: TangoMotor.isReady", self.name())
        return self.device.State == 'STANDBY'
        
        
    def connectNotify(self, signal):
        #logging.getLogger("HWR").info("%s: TangoMotor.connectNotify, : %s", self.name(), signal)
        if signal == 'hardwareObjectName,stateChanged':
            self.motorStateChanged(TangoMotor.stateDict[self.device.State])
        elif signal == 'limitsChanged':
            self.motorLimitsChanged()
            #print "Not implemented yet."
            
        elif signal == 'positionChanged':
            self.motorPositionChanged(self.device.position)
            
        self.setIsReady(True)
    
    def motorState(self):
        return TangoMotor.stateDict[self.device.State]
    
    def motorStateChanged(self, state):
        #logging.getLogger("HWR").info("%s: TangoMotor.motorStateChanged, %s", self.name(), state)
        #self.setIsReady(state == 'STANDBY')
        self.setIsReady(True)
        #print "motorStateChanged", str(state)
        try:
            self.emit('stateChanged', (TangoMotor.stateDict[self.device.State], ))
        except:
            pass
            #raise KeyError
            
    def getState(self):
        state = self.device.State
        #logging.getLogger("HWR").info("%s: TangoMotor.getState, %s", self.name(), state)
        return TangoMotor.stateDict[str(self.device.State())]
    
    def getLimits(self):
        position_info = self.device.attribute_query('position')
        low  = float(position_info.min_value)
        high = float(position_info.max_value)
        #limits = self.device.getLimits("position")
        #logging.getLogger("HWR").info("TangoMotor.getLimits: %.4f %.4f" % limits)
        return (low, high)
        
    def motorLimitsChanged(self):
        #self.emit('limitsChanged', (self.getLimits(), ))
        #logging.getLogger("HWR").info("%s: TangoMotor.limitsChanged", self.name())
        self.emit('limitsChanged', (self.getLimits(), )) 
                      
    def motorMoveDone(self, channelValue):
       #SpecMotorA.motorMoveDone(self, channelValue)
       #logging.getLogger("HWR").info("TangoMotor.motorMoveDone")
       if self.device.State == 'STANDBY':
           
          #self.emit('moveDone', (self.specversion, self.specname, ))
          self.emit('moveDone', ("EH3","toto" ))
          
    def motorPositionChanged(self, absolutePosition):
        self.emit('positionChanged', (absolutePosition, ))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        return '0' #NO ('1' means YES)
    
    def getPosition(self):
        pos = self.device.position
        #logging.getLogger("HWR").info("%s: TangoMotor.getPosition, pos = %.3f", self.name(), pos)
        return pos
    
    def syncMove(self, position):
        #print 'about to start moving', self.motorState
        t0 = time.time()
        prev_position = self.getPosition()
        self.device.position = position

        print 'move started from %s to %s, state is %s' % (prev_position, position, self.device.State)
        
        while self.device.State == "RUNNING" or self.device.State == "MOVING": # or self.device.State == SpecMotor.MOVESTARTED:
            #print 'processing events...', self.motorState
            qApp.processEvents(100)

        print 'move done (%s s), state is %s' % (time.time()-t0,  self.device.State)
        
    def moveRelative(self, position):
        old_pos = self.device.position
        self.device.position = old_pos + position
        #self.moveRelahardwareObjectName,tive(position)

        while self.device.State == "RUNNING" or self.device.State == "MOVING":
            qApp.processEvents(100)
        
    def syncMoveRelative(self, position):
        old_pos = self.device.position
        self.device.position = old_pos + position
        #self.moveRelahardwareObjectName,tive(position)

        while self.device.State == "RUNNING" or self.device.State == "MOVING":
            qApp.processEvents(100)
        

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
        self.device.position = absolutePosition

    def stop(self):
        logging.getLogger("HWR").info("TangoMotor.stop")
        self.device.Stop()

    def isSpecConnected(self):
        logging.getLogger().debug("%s: TangoMotor.isSpecConnected()" % self.name())
        return TruehardwareObjectName,
    
    

    
       

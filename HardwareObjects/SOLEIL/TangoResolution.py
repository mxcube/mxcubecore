import math
import logging
import time
import qt

from PyTango import DeviceProxy

from HardwareRepository import BaseHardwareObjects
from HardwareRepository import HardwareRepository
#from SpecClient import SpecCommand
# Changed for PILATUS 6M
DETECTOR_DIAMETER = 424.
# specState = {
#     'NOTINITIALIZED':   0,
#     'UNUSABLE':         1,
#     'READY':            2,
#     'MOVESTARTED':      3,
#     'MOVING':           4,
#     'ONLIMIT':          5}
class SpecMotor:
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

class TangoResolution(BaseHardwareObjects.Equipment):
#     resoState = {
#         None: 'unknown',
#         'UNKNOWN': 'unknown',
#         'CLOSE': 'closed',
#         'OPEN': 'opened',
#         'MOVING': 'moving',
#         'FAULT': 'fault',
#         'DISABLE': 'disabled',
#         'OFF': 'fault',
#         'ON': 'unknown'
#         }
        
    stateDict = {
         "UNKNOWN": 0,
         "ALARM":   1,
         "STANDBY": 2,
         "RUNNING": 4,
         "MOVING":  4,
         "1":       1,
         "2":       2}
   
    
    def _init(self):
        self.currentResolution = None
        self.currentDistance = None
        self.currentWavelength = None
        self.currentEnergy = None
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)
        self.device = DeviceProxy( self.getProperty("tangoname") )
        
        #self.monodevice = SimpleDevice(self.getProperty("tangoname2"), waitMoves = False, verbose=False)
        self.blenergyHOname = self.getProperty("BLEnergy")
        if self.blenergyHOname is None:
            logging.getLogger("HWR").error('TangoResolution: you must specify the %s hardware object' % self.blenergyHOname)
            hobj=None
            self.configOk=False
        else:
            hobj=HardwareRepository.HardwareRepository().getHardwareObject(self.blenergyHOname)
            if hobj is None:
                logging.getLogger("HWR").error('TangoResolution: invalid %s hardware object' % self.blenergyHOname)
                self.configOk=False
            self.blenergyHO=hobj
            self.connect(self.blenergyHO,qt.PYSIGNAL('energyChanged'), self.energyChanged)
        # creer un chanel sur l'energy: pour faire un update 
        positChan = self.getChannelObject("position") # utile seulement si statechan n'est pas defini dans le code
        positChan.connectSignal("update", self.positionChanged)
        stateChan = self.getChannelObject("state") # utile seulement si statechan n'est pas defini dans le code
        stateChan.connectSignal("update", self.stateChanged)
        
        self.currentDistance = self.device.position
        self.currentEnergy = self.blenergyHO.getCurrentEnergy()
        self.currentWavelength = self.blenergyHO.getCurrentWavelength()
        return BaseHardwareObjects.Equipment._init(self)

        
    def init(self):
        #self.detm = self.getDeviceByRole("detm")
        #self.dtox = self.getDeviceByRole("dtox")
        #self.dist2res = self.getCommandObject("dist2res")
        #self.res2dist = self.getCommandObject("res2dist")
        self.__resLimitsCallback = None
        
        
        self.__resLimitsErrCallback = None
        self.__resLimits = {}

        #self.connect(self.device, "stateChanged", self.detmStateChanged)
        #self.dist2res.connectSignal("commandReplyArrived", self.newResolution)
        #self.res2dist.connectSignal("commandReplyArrived", self.newDistance)
    
    def positionChanged(self, value):
        res = self.dist2res(value)
        self.emit('positionChanged', (res,))

    
    def getState(self):
        return TangoResolution.stateDict[str( self.device.State() )] 

                
    def equipmentReady(self):
        self.emit("deviceReady")


    def equipmentNotReady(self):
        self.emit("deviceNotReady")
        

    def getPosition(self):
        if self.currentResolution is None:
            self.recalculateResolution()
        return self.currentResolution

    def energyChanged(self, energy):
        if self.currentEnergy is None:
            self.currentEnergy = energy
        if type(energy) is not float:
            logging.getLogger("HWR").error("%s: TangoResolution Energy not a float: %s", energy, '')
            return
        if abs(self.currentEnergy - energy) > 0.0002:
            self.currentEnergy = energy # self.blenergyHO.getCurrentEnergy()
            self.wavelengthChanged(self.blenergyHO.getCurrentWavelength())
        
    def wavelengthChanged(self, wavelength):
        self.currentWavelength = wavelength
        self.recalculateResolution()
        
    def recalculateResolution(self):
        self.currentDistance = self.device.position
        self.currentResolution = self.dist2res(self.currentDistance)
        if self.currentResolution is None:
            return
        self.newResolution(self.currentResolution) 

    def newResolution(self, res):      
        if self.currentResolution is None:
            self.currentResolution = self.recalculateResolution()
        self.currentResolution = res
        self.emit("positionChanged", (res, ))
    
    def connectNotify(self, signal):
        #logging.getLogger("HWR").debug("%s: TangoResolution.connectNotify, : %s", \
        #                                                  self.name(), signal)
        if signal == "stateChanged":
            self.stateChanged(TangoResolution.stateDict[self.device.State])
        
        elif signal == 'positionChanged':
            self.positionChanged(self.device.position)

    def stateChanged(self, state):
        self.emit('stateChanged', (TangoResolution.stateDict[str(state)], ))


    def getLimits(self, callback=None, error_callback=None):

        positionChan = self.getChannelObject("position")
        info = positionChan.getInfo()

        high = float(info.max_value)
        low  = float(info.min_value)

        #logging.getLogger("HWR").debug("%s: DetectorDistance.getLimits: [%.2f - %.2f]" % (self.name(), low, high))
        
        if callable(callback):
            #logging.getLogger("HWR").debug("getLimits with callback: %s" % callback)

            self.__resLimitsCallback = callback
            self.__resLimitsErrCallback = error_callback

            self.__resLimits = {}
            rlow = self.dist2res(low, callback=self.__resLowLimitCallback, \
                                   error_callback=self.__resLimitsErrCallback)
            rhigh = self.dist2res(high, callback=self.__resHighLimitCallback,\
                                   error_callback=self.__resLimitsErrCallback)
        else:
            #logging.getLogger("HWR").debug("getLimits with no callback")
            rhigh  = self.dist2res(low)
            rlow   = self.dist2res(high)
        
        #logging.getLogger("HWR").debug("%s: TangoResolution.getLimits: [%.3f - %.3f]"\
                                                     #% (self.name(), rlow, rhigh))
        return (rlow, rhigh)


    def isSpecConnected(self):
        #logging.getLogger().debug("%s: TangoResolution.isSpecConnected()" % self.name())
        return True
    
    def __resLowLimitCallback(self, rlow):
        self.__resLimits["low"]=float(rlow)

        if len(self.__resLimits) == 2:
            if callable(self.__resLimitsCallback):
              self.__resLimitsCallback((self.__resLimits["low"], self.__resLimits["high"]))
            self.__resLimitsCallback = None
            self.__dist2resA1 = None
            self.__dist2resA2 = None


    def __resHighLimitCallback(self, rhigh):
        self.__resLimits["high"]=float(rhigh)

        if len(self.__resLimits) == 2:
            if callable(self.__resLimitsCallback):
              self.__resLimitsCallback((self.__resLimits["low"], self.__resLimits["high"]))
            self.__resLimitsCallback = None
            self.__dist2resA1 = None
            self.__dist2resA2 = None
            

    def __resLimitsErrCallback(self):
        if callable(self.__resLimitsErrCallback):
            self.__resLimitsErrCallback()
            self.__resLimitsErrCallback = None
            self.__dist2resA1 = None
            self.__dist2resA2 = None


    def move(self, res):
        self.currentWavelength = self.blenergyHO.getCurrentWavelength()
        self.device.position = self.res2dist(res)

    def newDistance(self, dist):
        self.device.position = dist


    def stop(self):
        try:
            self.device.Stop()
        except:
            logging.getLogger("HWR").err("%s: TangoResolution.stop: error while trying to stop!", self.name())
            pass
        
    def dist2res(self, Distance, callback=None, error_callback=None):

        Distance = float(Distance)
        try:
            #Wavelength = self.monodevice._SimpleDevice__DevProxy.read_attribute("lambda").value
            if self.currentWavelength is None:
                self.currentWavelength = self.blenergyHO.getCurrentWavelength()
            thetaangle2 = math.atan(DETECTOR_DIAMETER/2./Distance)
            Resolution = 0.5*self.currentWavelength /math.sin(thetaangle2/2.)
            if callable(callback):
                callback(Resolution)
            return Resolution
        except:
            if callable(error_callback):
                error_callback()

    
    def res2dist(self, Resolution):
        #print "********* In res2dist with ", Resolution
        Resolution = float(Resolution)
        #Wavelength = self.monodevice._SimpleDevice__DevProxy.read_attribute("lambda").value
        if self.currentWavelength is None:
            self.currentWavelength = self.blenergyHO.getCurrentWavelength()
        thetaangle=math.asin(self.currentWavelength / 2. / Resolution)
        Distance=DETECTOR_DIAMETER/2./math.tan(2.*thetaangle)
        #print "********* Distance ", Distance
        return Distance
    

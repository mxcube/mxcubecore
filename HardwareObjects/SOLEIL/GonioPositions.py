import logging
import time

#from PyTango import DeviceProxy
from HardwareRepository.Command.Tango import TangoCommand
from HardwareRepository.Command.Tango import DeviceProxy as HRDvProxy
from HardwareRepository.BaseHardwareObjects import Equipment

EPSILON = 0.03

class GonioPositions(Equipment):
    
    stateDict = {
         "UNKNOWN": 0,
         "ALARM":   1,
         "STANDBY": 2,
         "READY": 2,
         "RUNNING": 4,
         "MOVING":  4,
         '0': 0, '1': 1, '2': 2, '4': 4}

    def __init__(self, name):
        #logging.getLogger("HWR").info("MSCEquipment.__init__ of device")
        Equipment.__init__(self, name)
        self.current_distance = 450

    def _init(self):
        self.devices = self.getDevices()
        for dev in self.devices:
            try:
                logging.getLogger("HWR").info("Device found: %s" % dev.tangoname)
            except:
                pass
            #logging.getLogger("HWR").info("Device found: %s" % dev.tangoname)

        try:
            self.guillot = HRDvProxy(self.getProperty("tangoname_guillot"))
            self.microglide = HRDvProxy(self.getProperty("tangoname_microglide"))

            try:
                currentAuthorization = self.getChannelObject('GonioMovementAuthorized').getValue()
                self.authorizationChanged( currentAuthorization )
            except:
                import traceback
                traceback.print_exc()

            try:
                self.authorizationChannel = self.getChannelObject('GonioMovementAuthorized')
                self.authorizationChannel.connectSignal('update', self.authorizationChanged)
            except:
                import traceback
                traceback.print_exc()

            #print "---------------- SC ROBOT ------------------"
            #print self.authorizationChannel
            #print "--------------------------------------------"
            self.kappa    = self.getDeviceByRole("kappa")
            self.phi      = self.getDeviceByRole("phi")
            self.omega    = self.getDeviceByRole("omega")
            self.lightarm = self.getDeviceByRole("lightarm")
            self.zoom     = self.getDeviceByRole("zoom")
            self.obx      = self.getDeviceByRole("obx")
            self.detdist  = self.getDeviceByRole("detectordist")
        except:
#            self.errorDeviceInstance(self.getProperty("tangoname2"))
            logging.getLogger("HWR").error("%s: unknown device name",
                                                self.getProperty("tangoname"))
    
    def authorizationChanged(self,newvalue):
        self.emit("authorizationChanged", newvalue)
        logging.getLogger("HWR").debug("%s: GonioEquipment. Authorization from SC changed. Now is %s.", self.name(), newvalue )

    def Loading(self):
        try:
            logging.getLogger("HWR").debug("%s: GonioEquipment. Inserting Pilatus Guillotine.", self.name())
            try:
                self.guillot.Insert()
                self.microglide.Home()
                #self.current_distance = self.distance.position
                #if self.current_distance <= 450:
                #    self.distance.position = 450
            except:
                logging.getLogger("HWR").error("%s: GonioEquipment.. Error trying inserting Guillotine.", self.name())
        except:
            pass

        if abs(self.kappa.getPosition() - 55.) > EPSILON:
            self.kappa.move(55.)        
        if abs(self.omega.getPosition() + 17.) > EPSILON:
            self.omega.move(-17.)
        _obx = self.obx.getShutterState()
        print "OBX State = %s" % _obx
        if _obx == "opened":
            self.obx.closeShutter()
        _zoom = self.zoom.getCurrentPositionName()
        if _zoom != "Zoom 1":
            self.zoom.moveToPosition("Zoom 1")
        _light = self.lightarm.getWagoState()
        print "LIGHT POSITION:", _light
        if _light == "out":
            self.lightarm.wagoIn()
        self.state = "Centring"    

#        elif "obx" in device.tangoname.lower():
#            print "OBX STATE:", device.getShutterState()
#            if device.getShutterState() == "opened":
#                device.closeShutter()
#        elif "zoom" in device.tangoname.lower():
#            _zoom = device.getCurrentPositionName()
#            print "ZOOM POSITION:", _zoom
#            if _zoom != "Zoom 1":
#                device.moveToPosition("Zoom 1")
#        elif device.username == "Resolution":
#            print "Detector Distance", device.currentDistance
#            if device.currentDistance <= 350:
#                device.move(350.)
#            print device.tangoname, device.username #, device.getPosition()
#            #print device.getState()

    def Centring(self):
        #try:
        #    if self.current_distance > 195:
        #        self.distance.position = self.current_distance
        #except:
        #    logging.getLogger("HWR").error("%s: GonioEquipment.. Error trying mv back detector.", self.name())
        
        if abs(self.kappa.getPosition()) > EPSILON:
            self.kappa.move(0.)        
        if abs(self.omega.getPosition()) > EPSILON:
            self.omega.move(0.)
        _zoom = self.zoom.getCurrentPositionName()
        print "ZOOM POSITION:", _zoom
        if _zoom != "Zoom 1":
            self.zoom.moveToPosition("Zoom 1")
        _light = self.lightarm.getWagoState()
        print "LIGHT POSITION:", _light
        if _light == "out":
            self.lightarm.wagoIn()
        self.state = "Centring"    
            
    def wagoOut(self):
        self.Centring()
        
    def wagoIn(self):
        self.Loading()
        
#    def initAll(self):
#        initState = self.ms.getState()
#        self.ms.initAll()
#        state = self.ms.getState()
#        while state == initState:
#            print 'waiting state change...', state
#            qApp.processEvents(100)
#            state = self.ms.getState()
#        while state in ("MOVING", "DONE"):
#            print 'processing events...', state
#            qApp.processEvents(100)
#            state = self.ms.getState()
#        if state == "READY":
#            print "-----> emit stateChanged..."
#            self.emit("stateChanged", ["Kappa", "READY"])
#            self.emit("stateChanged", ["phi", "READY"])
#            devices = self.getDevices()
#            for device in devices:
#                device.getMscServer(self.ms)
#                device.motorStateChanged("READY")
               
    def initGoniometer(self):
        print "EUREKA :!!!!!!!!!!!!!!!!!!!!!!!"
        
    def isSpecConnected(self):
        #logging.getLogger().debug("%s: MSCEquipment.isSpecConnected()" % self.name())
        return True
    
    def isConnected(self):
        #logging.getLogger().debug("%s: MSCEquipment.isConnected()" % self.name())
        return True
    
    def isDisconnected(self):
        #logging.getLogger().debug("%s: MSCEquipment.isDisconnected()" % self.name())
        return True
    
    def isReady(self):
        #logging.getLogger("HWR").info("%s: MSCEquipment.isReady", self.name())
        return True
    
    def SCKappaOn(self):
        logging.getLogger("HWR").info("%s: MSCEquipment.SCKappaOn", self.name())

    def SCKappaOff(self):
        logging.getLogger("HWR").info("%s: MSCEquipment.SCKappaOff", self.name())        
    
    def getWagoState(self):
        if (abs(self.kappa.getPosition()) < EPSILON) and \
           (abs(self.omega.getPosition()) < EPSILON):
            self.state = "Centring"
            return self.state
        else :
            self.state = "Loading"
            return self.state

              
       

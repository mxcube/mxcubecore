import logging
import time

class MicroGlide2(TangoDCMotor):

    def __init__(self, name):

        TangoDCMotor.__init__(self, name)

    #def _init(self):
    #    self.devices = self.getDevices()
    #    for device in self.devices:
    #        logging.getLogger("HWR").info("OHOH device found : %s" % device.tangoname)
        #try:
        #    self.guillot = SimpleDevice(self.getProperty("tangoname_guillot"), verbose=False)
            #self.distance = SimpleDevice(self.getProperty("tangoname_distance"), waitMoves=False, verbose=False)
        #except:
#            self.errorDeviceInstance(self.getProperty("tangoname2"))
        #    logging.getLogger("HWR").error("%s: unknown device name",
        #                                       self.getProperty("tangoname"))
    
    def Loading(self):
        try:
            logging.getLogger("HWR").debug("%s: GonioEquipment. Inserting Pilatus Guillotine.", self.name())
            #try:
            #    self.guillot.Insert()
            #except:
            #    logging.getLogger("HWR").error("%s: GonioEquipment.. Error trying inserting Guillotine.", self.name())
        except:
            pass
        for device in self.devices:
            if "omega" in device.tangoname.lower():
                if device.getPosition() != -17.:
                    device.move(-17.)
            elif "kappa" in device.tangoname.lower():
                if device.getPosition() != 55.:
                    device.move(55.)
            elif "obx" in device.tangoname.lower():
                print "OBX STATE:", device.getShutterState()
                if device.getShutterState() == "opened":
                    device.closeShutter()
            elif "zoom" in device.tangoname.lower():
                _zoom = device.getCurrentPositionName()
                print "ZOOM POSITION:", _zoom
                if _zoom != "Zoom 1":
                    device.moveToPosition("Zoom 1")
            elif device.username == "Resolution":
                print "Detector Distance", device.currentDistance
                if device.currentDistance <= 350:
                    device.move(350.)
            print device.tangoname, device.username #, device.getPosition()
            #print device.getState()
        
    def Centring(self):

        for device in self.devices:
            if "kappa" in device.tangoname.lower():
                if abs(device.getPosition()) > 0.01:
                    device.move(0.)        
        for device in self.devices:
            if "omega" in device.tangoname.lower():
                if abs(device.getPosition()) > 0.01:
                    device.move(0.)
            
    def initAll(self):
        #initState = self.ms.getState()
        #self.ms.initAll()
        #state = self.ms.getState()
        while state == initState:
            print 'waiting state change...', state
            qApp.processEvents(100)
            state = self.ms.getState()
        while state in ("MOVING", "DONE"):
            print 'processing events...', state
            qApp.processEvents(100)
            state = self.ms.getState()
        if state == "READY":
            print "-----> emit stateChanged..."
            self.emit("stateChanged", ["Kappa", "READY"])
            self.emit("stateChanged", ["phi", "READY"])
            devices = self.getDevices()
               
    def initGoniometer(self):
        pass
    
    def initDetector(self):
        pass 
    
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
        logging.getLogger("HWR").info("%s: Equipment.SCKappaOn", self.name())

    def SCKappaOff(self):
        logging.getLogger("HWR").info("%s: Equipment.SCKappaOff", self.name())
    


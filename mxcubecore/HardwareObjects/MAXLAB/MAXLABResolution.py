from HardwareRepository import BaseHardwareObjects
import logging
import math


class MAXLABResolution(BaseHardwareObjects.Equipment):
    def _init(self):
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        return BaseHardwareObjects.Equipment._init(self)
        
    def init(self):
        self.currentResolution = None
        self.detmState = None 
        self.current_wavelength = 0
        self.energy = None

        self.detm = self.getDeviceByRole("detm")
        self.dtox = self.getDeviceByRole("dtox")
        self.wavelength = self.getDeviceByRole("wavelength")
        self.energy = self.getDeviceByRole("energy")
	self.getradius = self.getCommandObject("detector_radius")
   	self.detector_diameter_chan = self.addChannel({"type":"spec", "version": self.getradius.specVersion, "name":"detector_radius"}, "MXBCM_PARS/detector_radius")
        # some value has to be read, otherwise subsequent calls will fail due to some variables inside the buffer?????
         
        self.detector_diameter = 0
        self.det_radius = 0

        self.connect(self.detm, "stateChanged", self.detmStateChanged)
        self.connect(self.detm, "positionChanged", self.detmPositionChanged) 
     
        if self.wavelength is not None:
          self.connect(self.wavelength, "positionChanged", self.wavelengthChanged)
        else:
          if self.energy is None:
            # fixed wavelength
            self.connect(self.getwavelength, "connected", self.wavelengthChanged)
            if self.getwavelength.isConnected():
              self.wavelengthChanged()     
          else:
            self.connect(self.energy, "positionChanged", self.energyChanged)

        self.beam_centre_channel = self.addChannel({"type":"spec", "version": self.getradius.specVersion, "name":"beam_centre"}, "MXBCM_PARS/beam")   
        self.beam_centre_channel.connectSignal("update", self.beam_centre_updated)
        self.beam_centre_updated(self.beam_centre_channel.getValue())


    def beam_centre_updated(self, beam_pos_dict):
        if self.detector_diameter == 0:
            self.detector_diameter = float(self.detector_diameter_chan.getValue()) * 2
        x = float(beam_pos_dict["x"])
        y = float(beam_pos_dict["y"])
        self.det_radius =  min(self.detector_diameter - x, self.detector_diameter - y, x, y)

    def getWavelength(self):
        if self.wavelength is None:
          if self.energy is None:
            return self.getwavelength(wait=True)
          else:
            return 12.3984/self.energy.getPosition()
        else:
          return self.wavelength.getPosition()

    def wavelengthChanged(self, pos=None):
        if pos is None:
           pos = self.getWavelength()
        self.current_wavelength = pos
        self.recalculateResolution()      

    def energyChanged(self, energy):
        self.wavelengthChanged(12.3984/energy)
 
    def res2dist(self, res=None):
        self.current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2*math.asin(self.current_wavelength / (2*res))
            return self.det_radius / math.tan(ttheta)
        except:
            return None

    def dist2res(self, dist=None):
        
        if dist is None:
            dist = self.dtox.getPosition()
            
        try:
            ttheta = math.atan(self.det_radius / dist)
            
            if ttheta != 0:
                return self.current_wavelength / (2*math.sin(ttheta/2))
            else:
                return None
        except:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def recalculateResolution(self):
        new_res = self.dist2res(self.dtox.getPosition())
        if new_res is None:
            return
        self.newResolution(new_res) 

    def equipmentReady(self):
        self.emit("deviceReady")

    def equipmentNotReady(self):
        self.emit("deviceNotReady")

    def getPosition(self):
        if self.currentResolution is None:
          self.recalculateResolution()
        return self.currentResolution

    def get_value(self):
        return self.getPosition()
    
    def newResolution(self, res):
        self.currentResolution = res
        self.emit("positionChanged", (res, ))
        self.emit('valueChanged', (res, ))
         
    def getState(self):
        if self.detmState is None:
            return self.detm.getState()
        else:
            return self.detmState

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.detmStateChanged(self.detm.getState())

    def detmStateChanged(self, state):
        self.detmState = state

        if (state == self.detm.NOTINITIALIZED) or (state > self.detm.UNUSABLE):
          self.emit("stateChanged", (state, ))
          if state == self.detm.READY:
            self.recalculateResolution()
        else:
          self.detm.motorState = self.detm.READY
          self.detm.motorStateChanged(self.detm.motorState)

    def detmPositionChanged(self, pos):
        if self.motorIsMoving():
          return
        else:
          self.detmStateChanged(self.detm.READY)

    def getLimits(self, callback=None, error_callback=None):
        low, high = self.detm.getLimits()
       
        if callable(callback):
            callback((self.dist2res(low), self.dist2res(high)))
        else:    
            return (self.dist2res(low), self.dist2res(high))

    def move(self, pos, wait=True):
	logging.getLogger().info("move Resolution to %s", pos)
        if wait:
            self.newDistance(self.res2dist(pos)) 
        else:
            self.dtox.move(self.res2dist(pos))

    def motorIsMoving(self):
        return self.detm.motorIsMoving()

    def newDistance(self, dist):
        self.dtox.syncMove(dist)

    def stop(self):
        try:
            self.dtox.stop()
        except:
            pass
        try:
            self.detm.stop()
        except:
            pass

    

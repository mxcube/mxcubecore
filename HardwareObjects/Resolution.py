from HardwareRepository import BaseHardwareObjects
import logging
import math

class Resolution(BaseHardwareObjects.HardwareObject):
    def __init__(self, *args, **kwargs):
        BaseHardwareObjects.HardwareObject.__init__(self, *args, **kwargs)

        self.get_value = self.getPosition

    def init(self):
        self.currentResolution = None
        self.energy = None

        self.dtox = self.getObjectByRole("dtox")
        self.detector = self.getObjectByRole("detector")
        self.det_width = float(self.detector.getProperty('width'))
        self.det_height = float(self.detector.getProperty('height'))

        self.energy = self.getObjectByRole("energy")

        self.connect(self.dtox, "stateChanged", self.dtoxStateChanged)
        self.connect(self.dtox, "positionChanged", self.dtoxPositionChanged) 

    def isReady(self):
        try:
            return self.dtox.isReady()
        except:
            return False

    def get_beam_centre(self, dtox=None):
        if dtox is None:
            dtox = self.dtox.getPosition()

        ax = float(self.detector['beam'].getProperty('ax'))
        bx = float(self.detector['beam'].getProperty('bx'))
        ay = float(self.detector['beam'].getProperty('ay'))
        by = float(self.detector['beam'].getProperty('by'))
     
        return float(dtox*ax+bx), float(dtox*ay+by)

    def update_beam_centre(self, dtox):
        beam_x, beam_y = self.get_beam_centre(dtox)
        self.det_radius =  min(self.det_width - beam_x, self.det_height - beam_y, beam_x, beam_y)

    def getWavelength(self):
        return self.energy.getCurrentWavelength()

    def res2dist(self, res=None):
        current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2*math.asin(current_wavelength / (2*res))
            return self.det_radius / math.tan(ttheta)
        except:
            return None

    def _calc_res(self, radius, dist):
        current_wavelength = self.getWavelength()

        try:
            ttheta = math.atan(radius / dist)
            
            if ttheta != 0:
                return current_wavelength / (2*math.sin(ttheta/2))
            else:
                return None
        except:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def dist2res(self, dist=None):
        if dist is None:
            dist = self.dtox.getPosition()
            
        return self._calc_res(self.det_radius, dist)
       
    def recalculateResolution(self):
        dtox_pos = self.dtox.getPosition()
        self.update_beam_centre(dtox_pos)
        new_res = self.dist2res(dtox_pos)
        if new_res is None:
            return
        self.update_resolution(new_res) 

    def getPosition(self):
        if self.currentResolution is None:
          self.recalculateResolution()
        return self.currentResolution

    def get_value_at_corner(self):
        dtox_pos = self.dtox.getPosition()
        beam_x, beam_y = self.get_beam_centre(dtox_pos)

        distance_at_corners = [math.sqrt(beam_x**2+beam_y**2), 
                               math.sqrt((self.det_width-beam_x)**2+beam_y**2),
                               math.sqrt((beam_x**2+(self.det_height-beam_y)**2)),
                               math.sqrt((self.det_width-beam_x)**2+(self.det_height-beam_y)**2)]
        return self._calc_res(max(distance_at_corners), dtox_pos)      

    
    def update_resolution(self, res):
        self.currentResolution = res
        self.emit("positionChanged", (res, ))
        self.emit('valueChanged', (res, ))
         
    def getState(self):
        return self.dtox.getState()

    def connectNotify(self, signal):
        if signal == "stateChanged":
            self.dtoxStateChanged(self.dtox.getState())

    def dtoxStateChanged(self, state):
        if (state == self.dtox.NOTINITIALIZED) or (state > self.dtox.UNUSABLE):
          self.emit("stateChanged", (state, ))
          if state == self.dtox.READY:
            self.recalculateResolution()
        else:
          self.dtox.motorState = self.dtox.READY
          self.dtox.motorStateChanged(self.dtox.motorState)

    def dtoxPositionChanged(self, pos):
        self.update_beam_centre(pos)
        self.update_resolution(self.dist2res(pos))

    def getLimits(self):
        low, high = self.dtox.getLimits()
       
        return (self.dist2res(low), self.dist2res(high))

    def move(self, pos, wait=False):
	logging.getLogger().info("move Resolution to %s", pos)
        if wait:
          self.dtox.syncMove(self.res2dist(pos))
        else:
          self.dtox.move(self.res2dist(pos))

    def motorIsMoving(self):
        return self.dtox.motorIsMoving()

    def stop(self):
        try:
            self.dtox.stop()
        except:
            pass
    

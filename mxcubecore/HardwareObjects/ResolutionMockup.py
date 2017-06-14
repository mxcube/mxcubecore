from HardwareRepository import BaseHardwareObjects
import logging
import math


class ResolutionMockup(BaseHardwareObjects.Equipment):
    def _init(self):
        self.connect("equipmentReady", self.equipmentReady)
        self.connect("equipmentNotReady", self.equipmentNotReady)

        return BaseHardwareObjects.Equipment._init(self)

    def init(self):
        self.currentResolution = 3
        self.detmState = None
        self.det_radius = 100
        self.state = 2
        self.dtox = self.getObjectByRole("dtox")
        self.energy = self.getObjectByRole("energy")
        self.detector = self.getObjectByRole("detector")
        self.connect(self.dtox, "positionChanged", self.dtoxPositionChanged)
        self.dtox.move(self.res2dist(self.currentResolution))

    def beam_centre_updated(self, beam_pos_dict):
        pass

    def dtoxPositionChanged(self, pos):
        self.newResolution(self.dist2res(pos))

    def getWavelength(self):
        return self.energy.getCurrentWavelength()

    def wavelengthChanged(self, pos=None):
        self.recalculateResolution(pos)

    def energyChanged(self, energy):
        self.wavelengthChanged(12.3984 / energy)

    def res2dist(self, res=None):
        self.current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2 * math.asin(self.getWavelength() / (2 * res))
            return self.det_radius / math.tan(ttheta)
        except:
            return None

    def dist2res(self, dist=None):
        try:
            ttheta = math.atan(self.det_radius / dist)
            if ttheta != 0:
                return self.getWavelength() / (2 * math.sin(ttheta / 2))
        except:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def recalculateResolution(self):
        self.currentResolution = self.dist2res(self.dtox.getPosition())

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
        if res:
            self.currentResolution = res
            self.emit("positionChanged", (res, ))
            self.emit('valueChanged', (res, ))

    def getState(self):
        return self.state

    def connectNotify(self, signal):
        pass

    def detmStateChanged(self, state):
        pass

    def detmPositionChanged(self, pos):
        pass

    def getLimits(self, callback=None, error_callback=None):
        return (0, 20)

    def move(self, pos, wait=True):
        self.dtox.move(self.res2dist(pos))

    def motorIsMoving(self):
        return self.dtox.motorIsMoving() or self.energy.moving

    def newDistance(self, dist):
        pass

    def stop(self):
        self.dtox.stop()

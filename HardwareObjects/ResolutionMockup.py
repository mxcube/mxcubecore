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
        self.current_wavelength = 10
        self.energy = 12

    def beam_centre_updated(self, beam_pos_dict):
        pass

    def getWavelength(self):
        if self.wavelength is None:
            if self.energy is None:
                return self.getwavelength(wait=True)
            else:
                return 12.3984 / self.energy.getPosition()
        else:
            return self.wavelength.getPosition()

    def wavelengthChanged(self, pos=None):
        if pos is None:
            pos = self.getWavelength()
        self.current_wavelength = pos
        self.recalculateResolution()

    def energyChanged(self, energy):
        self.wavelengthChanged(12.3984 / energy)

    def res2dist(self, res=None):
        self.current_wavelength = self.getWavelength()

        if res is None:
            res = self.currentResolution

        try:
            ttheta = 2 * math.asin(self.current_wavelength / (2 * res))
            return self.det_radius / math.tan(ttheta)
        except:
            return None

    def dist2res(self, dist=None):
        dist = 520

        try:
            ttheta = math.atan(self.det_radius / dist)
            return self.current_wavelength / (2 * math.sin(ttheta / 2))
        except:
            logging.getLogger().exception("error while calculating resolution")
            return None

    def recalculateResolution(self):
        pass

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
        pass

    def connectNotify(self, signal):
        pass

    def detmStateChanged(self, state):
        pass

    def detmPositionChanged(self, pos):
        pass

    def getLimits(self, callback=None, error_callback=None):
        return (0, 20)

    def move(self, pos, wait=True):
        logging.getLogger().info("move Resolution to %s", pos)

    def motorIsMoving(self):
        return False

    def newDistance(self, dist):
        pass

    def stop(self):
        pass

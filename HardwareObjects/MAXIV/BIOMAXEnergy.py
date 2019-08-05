import logging
import gevent
from HardwareRepository.HardwareObjects import Energy
from HardwareRepository import HardwareRepository
beamline_object = HardwareRepository.get_beamline()


class BIOMAXEnergy(Energy.Energy):
    def __init__(self, *args, **kwargs):
        Energy.Energy.__init__(self, *args, **kwargs)

    def init(self):
        self.ready_event = gevent.event.Event()
        self.tunable = False
        self.moving = None
        self.default_en = None
        self.ctrl = None
        self.en_lims = []

        try:
            self.default_en = self.getProperty("default_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: no default energy")

        try:
            self.tunable = self.getProperty("tunable_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: will set to fixed energy")

        try:
            self.ctrl = self.getObjectByRole("controller")
        except KeyError:
            logging.getLogger("HWR").info("No controller used")

        if beamline_object.energy is not None:
            beamline_object.energy.connect("positionChanged", self.energyPositionChanged)
            beamline_object.energy.connect("stateChanged", self.energyStateChanged)

    def get_current_energy(self):
        if beamline_object.energy is not None:
            try:
                return beamline_object.energy.getPosition() / 1000
            except BaseException:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read current energy"
                )
                return None
        return self.default_en

    def getEnergyLimits(self):
        if not self.tunable:
            return None

        if beamline_object.energy is not None:
            try:
                self.en_lims = beamline_object.energy.getLimits()
                self.en_lims = (
                    float(self.en_lims[0]) / 1000,
                    float(self.en_lims[1]) / 1000,
                )
                return self.en_lims
            except BaseException:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read energy motor limits"
                )
                return None
        return None

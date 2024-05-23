import logging
import gevent
from mxcubecore.HardwareObjects import Energy
from mxcubecore import HardwareRepository as HWR


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
            self.default_en = self.get_property("default_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: no default energy")

        try:
            self.tunable = self.get_property("tunable_energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: will set to fixed energy")

        try:
            self.ctrl = self.get_object_by_role("controller")
        except KeyError:
            logging.getLogger("HWR").info("No controller used")

        if HWR.beamline.config.energy is not None:
            HWR.beamline.config.energy.connect("valueChanged", self.energyPositionChanged)
            HWR.beamline.config.energy.connect("stateChanged", self.energyStateChanged)

    # def get_current_energy(self):
    #     if HWR.beamline.config.energy is not None:
    #         try:
    #             return HWR.beamline.config.energy.get_value() / 1000
    #         except Exception:
    #             logging.getLogger("HWR").exception(
    #                 "EnergyHO: could not read current energy"
    #             )
    #             return None
    #     return self.default_en

    def get_limits(self):
        if not self.tunable:
            return None

        if HWR.beamline.config.energy is not None:
            try:
                self.en_lims = HWR.beamline.config.energy.get_limits()
                self.en_lims = (
                    float(self.en_lims[0]) / 1000,
                    float(self.en_lims[1]) / 1000,
                )
                return self.en_lims
            except Exception:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read energy motor limits"
                )
                return None
        return None

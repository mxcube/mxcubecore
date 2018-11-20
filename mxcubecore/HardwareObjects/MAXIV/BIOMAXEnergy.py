import sys
import time
import logging
import math
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *
import Energy


class BIOMAXEnergy(Energy.Energy):
    def __init__(self, *args, **kwargs):
        Energy.Energy.__init__(self, *args, **kwargs)

    def init(self):
        self.ready_event = gevent.event.Event()
        self.energy_motor = None
        self.tunable = False
        self.moving = None
        self.default_en = None
        self.ctrl = None
        self.en_lims = []

        try:
            self.energy_motor = self.getObjectByRole("energy")
        except KeyError:
            logging.getLogger("HWR").warning("Energy: error initializing energy motor")

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

        if self.energy_motor is not None:
            self.energy_motor.connect("positionChanged", self.energyPositionChanged)
            self.energy_motor.connect("stateChanged", self.energyStateChanged)

    def getCurrentEnergy(self):
        if self.energy_motor is not None:
            try:
                return self.energy_motor.getPosition() / 1000
            except:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read current energy"
                )
                return None
        return self.default_en

    def getEnergyLimits(self):
        if not self.tunable:
            return None

        if self.energy_motor is not None:
            try:
                self.en_lims = self.energy_motor.getLimits()
                self.en_lims = (
                    float(self.en_lims[0]) / 1000,
                    float(self.en_lims[1]) / 1000,
                )
                return self.en_lims
            except:
                logging.getLogger("HWR").exception(
                    "EnergyHO: could not read energy motor limits"
                )
                return None
        return None

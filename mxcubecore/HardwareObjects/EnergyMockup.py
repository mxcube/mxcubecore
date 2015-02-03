import sys
import time
import logging
import math
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *

class EnergyMockup(Equipment):

class EnergyScan(Equipment):
   def init(self):
       self.ready_event = gevent.event.Event()
       self.energy_motor = None
       self.tunable = False
       self.moving = None
       self.default_en = 0
       self.en_lims = []

    def canMoveEnergy(self):
        return self.tunable

    def isConnected(self):
        return True

    def getCurrentEnergy(self):
        return self.default_en

   def getCurrentWavelength(self):
        current_en = self.getCurrentEnergy()
        if current_en is not None:
            return (12.3984/current_en)
        return None

   def getEnergyLimits(self):
        return None

   def getWavelengthLimits(self):
        lims = None
        self.en_lims = self.getEnergyLimits()
        if self.en_lims is not None:
            lims=(12.3984/self.en_lims[1], 12.3984/self.en_lims[0])
        return lims

  def startMoveEnergy(self, value, wait=True):
      return

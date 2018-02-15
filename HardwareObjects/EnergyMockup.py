import time
from General import h_over_e

from HardwareRepository.BaseHardwareObjects import Equipment


class EnergyMockup(Equipment):
   def init(self):
       self.energy_motor = None
       self.tunable = True
       self.moving = False
       self.default_en = 12.0
       self.en_lims = []
       self.energy_value = 12.0
       self.wavelength_value = h_over_e/self.energy_value

       self.canMoveEnergy = self.can_move_energy
       self.move_energy = self.start_move_energy 
       self.getEnergyLimits  = self.get_energy_limits
       self.get_wavelength_limits = self.getWavelengthLimits
       self._abort = False

   def update_values(self):
       self.emit("energyChanged", self.energy_value, self.wavelength_value)

   def abort(self):
       self._abort = True

   def can_move_energy(self):
       return self.tunable

   def isConnected(self):
       return True

   def getCurrentEnergy(self):
       return self.energy_value

   def getCurrentWavelength(self):
       current_en = self.getCurrentEnergy()
       if current_en is not None:
           return (h_over_e/current_en)
       return None

   def get_energy_limits(self):
       return [4, 20]

   def getWavelengthLimits(self):
       lims = None
       self.en_lims = self.getEnergyLimits()
       if self.en_lims is not None:
           lims=(h_over_e/self.en_lims[1], h_over_e/self.en_lims[0])
       return lims

   def start_move_energy(self, value, wait=True):
       if wait:
           self._abort = False
           self.moving = True

          # rhfogh: Modified as previous allowed only integer values
          # First move towards energy, setting to integer keV values
           step = -1 if value < self.energy_value else 1
           for ii in range(int(self.energy_value) +step , int(value) + step,
                          step):
               if self._abort:
                   self.moving = False
                   raise StopIteration("Energy change cancelled !")

               self.energy_value = ii
               self.wavelength_value = h_over_e / ii
               self.update_values()
               time.sleep(0.2)

       # Now set final value
       self.energy_value = value
       self.wavelength_value = h_over_e / value
       self.update_values()

       self.moving = False

   def move_wavelength(self, value, wait=True):
       self.start_move_energy(h_over_e / value, wait)

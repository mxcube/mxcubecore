from HardwareRepository.BaseHardwareObjects import Equipment

class EnergyMockup(Equipment):
   def init(self):
       self.energy_motor = None
       self.tunable = True
       self.moving = None
       self.default_en = 12
       self.en_lims = []
       self.energy_value = 12
       self.wavelength_value = 12.3984/self.energy_value

       self.canMoveEnergy = self.can_move_energy
       self.move_energy = self.start_move_energy 
       self.getEnergyLimits  = self.get_energy_limits

   def update_values(self):
       self.emit("energyChanged", self.energy_value, self.wavelength_value)

   def can_move_energy(self):
       return self.tunable

   def isConnected(self):
       return True

   def getCurrentEnergy(self):
       return self.energy_value

   def getCurrentWavelength(self):
       current_en = self.getCurrentEnergy()
       if current_en is not None:
           return (12.3984/current_en)
       return None

   def get_energy_limits(self):
       return None

   def getWavelengthLimits(self):
       lims = None
       self.en_lims = self.getEnergyLimits()
       if self.en_lims is not None:
           lims=(12.3984/self.en_lims[1], 12.3984/self.en_lims[0])
       return lims

   def start_move_energy(self, value, wait=True):      
      if wait:
         self._abort = False
          
         if value > self.energy_value:
            r = range(self.energy_value, int(value) + 1)
         elif value < self.energy_value:
            r = range(self.energy_value, int(value) - 1, -1)
         else:
            r = [value]
            
         for x in r:
            if self._abort:
               raise StopIteration("Energy change canceled !")

            self.energy_value = x
            self.update_values()
            time.sleep(0.2)
      else:
         self.energy_value = value
         self.update_values()
               
             

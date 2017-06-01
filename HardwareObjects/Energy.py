import sys
import time
import logging
import math
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *

"""
Example xml file:
  - for tunable wavelength beamline:
<object class="Energy">
  <object href="/energy" role="energy"/>
  <object href="/khoros" role="controller"/>
  <tunable_energy>True</tunable_energy>
</object>
The energy should have methods getPosition, getLimits and move.
If used, the controller should have method moveEnergy.

  - for fixed wavelength beamline:
<object class="Energy">
  <default_energy>12.8123</tunable_energy>
</object>
"""
class Energy(Equipment):

    def init(self):
        self.ready_event = gevent.event.Event()
        self.energy_motor = None
        self.tunable = False
        self.moving = None
        self.default_en = None
        self.ctrl = None
        self.en_lims = []

        try:
            self.energy_motor =  self.getObjectByRole("energy")
        except KeyError:
            logging.getLogger("HWR").warning('Energy: error initializing energy motor')

        try:
            self.default_en = self.getProperty("default_energy")
        except KeyError:
            logging.getLogger("HWR").warning('Energy: no default energy')

        try:
            self.tunable = self.getProperty("tunable_energy")
        except KeyError :
            logging.getLogger("HWR").warning('Energy: will set to fixed energy')

        try:
            self.ctrl = self.getObjectByRole("controller")
        except KeyError:
            logging.getLogger("HWR").info("No controller used")

        if self.energy_motor is not None:
            self.energy_motor.connect('positionChanged', self.energyPositionChanged)
            self.energy_motor.connect('stateChanged', self.energyStateChanged)

    """
    read tunable_energy from the HO, return True/False
    """
    def canMoveEnergy(self):
        return self.tunable
    
    def isConnected(self):
        return True

    def getCurrentEnergy(self):
        logging.getLogger('user_level_log').debug("Get current energy")
        if self.energy_motor is not None:
            try:
                return self.energy_motor.getPosition()
            except:
                logging.getLogger("HWR").exception("EnergyHO: could not read current energy")
                return None
        return self.default_en

    def getCurrentWavelength(self):
        #logging.getLogger('user_level_log').debug("Get current wavelength")
        current_en = self.getCurrentEnergy()
        if current_en:
            return (12.3984/current_en)
        return None

    def getEnergyLimits(self):
        logging.getLogger("HWR").debug("Get energy limits")
        if not self.tunable:
            return None

        if self.energy_motor is not None:
            try:
                self.en_lims = self.energy_motor.getLimits()
                return self.en_lims 
            except:
                logging.getLogger("HWR").exception("EnergyHO: could not read energy motor limits")
                return None
        return None 

    def getWavelengthLimits(self):
        logging.getLogger("HWR").debug("Get wavelength limits")
        if not self.tunable:
            return None
        self.en_lims = self.getEnergyLimits()
        if self.en_lims:
            lims=(12.3984/self.en_lims[1], 12.3984/self.en_lims[0])
        return lims
            
    """
    the energy is in keV
    """
    def startMoveEnergy(self, value, wait=True):
        if not self.tunable:
            return False

        try:
            value=float(value)
        except (TypeError,ValueError) as diag:
            logging.getLogger('user_level_log').error("Energy: invalid energy (%s)" % value)
            return False

        current_en = self.getCurrentEnergy()
        if current_en:
            if math.fabs(value - current_en) < 0.001:
                self.moveEnergyCmdFinished(True)
        if self.checkLimits(value) is False:
            return False

        self.moveEnergyCmdStarted()
        def change_egy():
            try:
                self.move_energy(value, wait=True)
            except:
                self.moveEnergyCmdFailed()
            else:
                self.moveEnergyCmdFinished(True)
        if wait:
            change_egy()
        else:
            gevent.spawn(change_egy)

    def moveEnergyCmdStarted(self):
        self.moving = True
        self.emit('moveEnergyStarted', ())
    def moveEnergyCmdFailed(self):
        self.moving = False
        self.emit('moveEnergyFailed', ())
    def moveEnergyCmdAborted(self):
        pass
        #self.moving = False
        #self.emit('moveEnergyFailed', ())

    def moveEnergyCmdFinished(self,result):
        self.moving = False
        self.emit('moveEnergyFinished', ())       
            
    def checkLimits(self, value):
        logging.getLogger("HWR").debug("Checking the move limits")
        if self.getEnergyLimits():
            if value >= self.en_lims[0] and value <= self.en_lims[1]:
                logging.getLogger("HWR").info("Limits ok")
                return True
            logging.getLogger('user_level_log').info("Requested value is out of limits")
        return False
        
    def startMoveWavelength(self, value, wait=True):
        logging.getLogger("HWR").info("Moving wavelength to (%s)" % value)
        return self.startMoveEnergy(12.3984/value, wait)

    def cancelMoveEnergy(self):
        logging.getLogger('user_level_log').info("Cancel move")
        self.moveEnergy.abort()

    def move_energy(self, energy, wait=True):
        current_en = self.getCurrentEnergy()
        pos = math.fabs(current_en - energy)
        if pos < 0.001:
            logging.getLogger('user_level_log').debug("Energy: already at %g, not moving", energy)
        else:
            logging.getLogger('user_level_log').debug("Energy: moving energy to %g", energy)
            if pos > 0.02:
                try:
                    if self.ctrl:
                        self.ctrl.moveEnergy(energy)
                        self.ctrl.quick_realign()
                    else:
                        self.executeCommand("moveEnergy", energy, wait=True)
                except RuntimeError as AttributeError:
                    self.energy_motor.move(energy)
            else:
                self.energy_motor.move(energy)

    def energyPositionChanged(self,pos):
        wl=12.3984/pos
        if wl:
            self.emit('energyChanged', (pos,wl))
            self.emit('valueChanged', (pos, ))

    def energyStateChanged(self, state):
        print(state)

    def get_value(self):
        #generic method used by the beamline setup
        return self.getCurrentEnergy()

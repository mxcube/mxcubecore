#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
EMBLEnergy
"""

import math
import logging
from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import *


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLEnergy(Device):

    (READY, MOVING) = (0, 1)

    def __init__(self, name):
        Device.__init__(self, name)

        self.ready_event = None
        self.tunable = False
        self.current_energy = 0
        self.current_wav = 0
        self.moving = None
        self.default_en = 0
        self.en_lims = [None, None]
        self.undulator_gaps = []

        self.cmd_set_energy = None
        self.chan_energy = None
        self.chan_limit_low = None
        self.chan_limit_high = None
        self.chan_status = None
        self.chan_undulator_gaps = None

    def init(self):
        self.ready_event = gevent.event.Event()

        self.cmd_set_energy = self.getCommandObject('cmdSetEnergy')

        self.chan_energy = self.getChannelObject('chanEnergy')
        if self.chan_energy is not None: 
            self.chan_energy.connectSignal('update', self.energyPositionChanged)
        
        self.chan_limit_low = self.getChannelObject('chanLimitLow')
        if self.chan_limit_low is not None:  
            self.chan_limit_low.connectSignal('update', self.energyLimitsChanged) 

        self.chan_limit_high = self.getChannelObject('chanLimitHigh')
        if self.chan_limit_high is not None:
            self.chan_limit_high.connectSignal('update', self.energyLimitsChanged)

        self.chan_status = self.getChannelObject('chanStatus')
        if self.chan_status is not None:
            self.chan_status.connectSignal('update', self.energyStateChanged) 

        self.chan_undulator_gaps = self.getChannelObject('chanUndulatorGap')

        if self.chan_undulator_gaps is not None:
            self.chan_undulator_gaps.connectSignal('update', self.undulator_gaps_changed)
        
        try:
            self.tunable = self.getProperty("tunableEnergy")
        except:
            logging.getLogger("HWR").warning('Energy: will set to fixed energy')

        try:
            self.default_en = self.getProperty("defaultEnergy")
        except:
            logging.getLogger("HWR").warning('Energy: no default energy defined')

        try:
            self.en_lims = eval(self.getProperty("staticLimits"))
        except:
            self.en_lims = [None, None]

        self.get_energy_limits = self.getEnergyLimits
        if not self.chan_energy:
            self.energyPositionChanged(self.default_en * 1000)

    def can_move_energy(self):
        return self.tunable
    
    def isConnected(self):
        return True

    def isReady(self):
        return True

    def getCurrentEnergy(self):
        value = self.default_en
        if self.chan_energy is not None:
            try:
                value = self.chan_energy.getValue()
                return value[0]/1000
            except:
                logging.getLogger("HWR").exception("Energy: could not read current energy")
                return None
        return value

    def getCurrentWavelength(self):
        #logging.getLogger("HWR").info("Get current wavelength")
        current_en = self.getCurrentEnergy()
        if current_en is not None:
            return (12.3984/current_en)
        return None

    def getEnergyLimits(self):
        #self.en_lims = [0.01, 15]
        if (self.chan_limit_low is not None and \
            self.chan_limit_high is not None):
            try:
                self.en_lims[0] = self.chan_limit_low.getValue()
                self.en_lims[1] = self.chan_limit_high.getValue()
            except:
                logging.getLogger("HWR").exception("Energy: could not read energy limits")
        return self.en_lims

    def getWavelengthLimits(self):
        #logging.getLogger("HWR").info("Get wavelength limits")
        lims = None
        self.en_lims = self.getEnergyLimits()
        if self.en_lims is not None:
            lims = (12.3984 / self.en_lims[1], 12.3984 / self.en_lims[0])
        return lims
            
    """
    the energy is in keV
    """
    def startMoveEnergy(self, value, wait=True):
        try:
            value = float(value)
        except (TypeError, ValueError), diag:
            logging.getLogger('user_level_log').error("Energy: invalid energy (%s)" % value)
            return False

        #current_en = self.getCurrentEnergy()
        """
        if current_en is not None:
            if math.fabs(value - current_en) < 0.001:
                self.moveEnergyCmdFinished(True)
        """
        if self.checkLimits(value) is False:
            return False
        self.moveEnergyCmdStarted()
        def change_egy():
            try:
                self.move_energy(value, wait=True)
            except:
                self.moveEnergyCmdFailed()
            #else:
            #    self.moveEnergyCmdFinished(True)
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
        self.moving = False
        self.emit('moveEnergyFailed', ())

    def moveEnergyCmdFinished(self, result):
        self.moving = False
        self.emit('moveEnergyFinished', ())       
            
    def checkLimits(self, value):
        logging.getLogger("HWR").info("Checking the move limits")
        if value >= self.en_lims[0] and value <= self.en_lims[1]:
            logging.getLogger("HWR").info("Limits ok")
            return True
        logging.getLogger().info("Requested value is out of limits")
        return False
        
    def startMoveWavelength(self, value, wait=True):
        logging.getLogger("HWR").info("Moving wavelength to (%s)" % value)
        return self.startMoveEnergy(12.3984/value, wait)
        #return self.startMoveEnergy(value, wait)

    def cancelMoveEnergy(self):
        logging.getLogger('user_level_log').info("Cancel move")
        #self.moveEnergy.abort()

    def move_energy(self, energy, wait=True):
        """
        Descript. : in our case we set walelength
        """ 
        current_en = self.getCurrentEnergy()
        pos = math.fabs(current_en - energy)
        if pos < 0.001:
            logging.getLogger('user_level_log').debug("Energy: already at %g, not moving", energy)
            self.emit('energyStateChanged', ('ready', ))
        else:
            logging.getLogger('user_level_log').debug("Energy: moving energy to %g", energy)
            if self.cmd_set_energy:
                self.cmd_set_energy(energy)
            else:
                #Mockup mode
                self.energyPositionChanged([energy * 1000])

    def energyPositionChanged(self, pos):
        #self.moveEnergyCmdFinished(True)
        if type(pos) in (list, tuple):
            pos = pos[0]
        energy = pos / 1000
        if abs(energy - self.current_energy) > 1e-2:
            self.current_energy = energy
            self.current_wav = 12.3984 / energy
            if self.current_wav is not None:
                self.emit('energyChanged', (self.current_energy, self.current_wav))
                self.emit('valueChanged', (self.current_energy, ))

    def energyLimitsChanged(self, limit):
        limits = self.getEnergyLimits()
        self.emit('energyLimitsChanged', (limits,))

    def energyStateChanged(self, state):
        state = int(state[0])
        if state == 0:
            self.moveEnergyCmdFinished(0)
        elif state == 1:
            self.moveEnergyCmdStarted()
        self.emit('energyStateChanged', (state,))

    def get_value(self):
        #generic method to be used by beamline setup
        return self.getCurrentEnergy()

    def update_values(self):
        self.emit('energyChanged', (self.current_energy, self.current_wav))
        self.emit('valueChanged', (self.current_energy, ))

    def undulator_gaps_changed(self, value):
        if type(value) in (list, tuple):
            self.undulator_gaps = [value[0]]
        else:
            self.undulator_gaps = [value]

    def get_undulator_gaps(self):
        if self.chan_undulator_gaps:
            self.undulator_gaps_changed(self.chan_undulator_gaps.getValue()) 
        return self.undulator_gaps

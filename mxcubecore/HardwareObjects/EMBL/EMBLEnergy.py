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

import gevent
import logging
from time import sleep
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLEnergy(Device):


    def __init__(self, name):
        Device.__init__(self, name)

        self.ready_event = None
        self.tunable = False
        self.current_energy = 0
        self.current_wav = 0
        self.moving = None
        self.default_en = 0
        self.limits = [None, None]
        self.undulator_gaps = []
        self.ctrl_bytes = None
        self.bragg_break_status = None

        self.chan_energy = None
        self.chan_limit_low = None
        self.chan_limit_high = None
        self.chan_status = None
        self.chan_undulator_gaps = None
        self.chan_status_bragg_break = None
        self.cmd_set_energy = None
        self.cmd_energy_ctrl_byte = None
        self.cmd_set_break_bragg = None
        self.cmd_release_break_bragg = None

    def init(self):
        self.moving = False
        self.ready_event = gevent.event.Event()

        try:
            self.limits = eval(self.getProperty("staticLimits"))
        except:
            self.limits = [None, None]

        self.cmd_set_energy = \
             self.getCommandObject('cmdSetEnergy')
        self.cmd_energy_ctrl_byte = \
             self.getCommandObject('cmdEnergyCtrlByte')
        self.cmd_set_break_bragg = \
             self.getCommandObject('cmdSetBreakBragg')
        self.cmd_release_break_bragg = \
             self.getCommandObject('cmdReleaseBreakBragg')

        self.chan_energy = self.getChannelObject('chanEnergy')
        if self.chan_energy is not None:
            self.chan_energy.connectSignal('update',
                                           self.energy_position_changed)

        self.chan_limit_low = self.getChannelObject('chanLimitLow')
        if self.chan_limit_low is not None:
            self.chan_limit_low.connectSignal('update',
                                              self.energy_limits_changed)

        self.chan_limit_high = self.getChannelObject('chanLimitHigh')
        if self.chan_limit_high is not None:
            self.chan_limit_high.connectSignal('update',
                                               self.energy_limits_changed)

        self.chan_status = self.getChannelObject('chanStatus')
        if self.chan_status is not None:
            self.chan_status.connectSignal('update',
                                           self.energy_state_changed)

        self.chan_undulator_gaps = self.getChannelObject('chanUndulatorGap')
        if self.chan_undulator_gaps is not None:
            self.chan_undulator_gaps.connectSignal('update',
                                                   self.undulator_gaps_changed)

        self.chan_status_bragg_break = self.getChannelObject('chanStatusBraggBreak')
        if self.chan_status_bragg_break is not None:  
            self.chan_status_bragg_break.connectSignal('update',
                                                        self.bragg_break_status_changed)

        try:
            self.tunable = self.getProperty("tunableEnergy")
        except:
            logging.getLogger("HWR").warning('Energy: will set to fixed energy')
        try:
            self.default_en = self.getProperty("defaultEnergy")
        except:
            logging.getLogger("HWR").warning('Energy: no default energy defined')

        self.ctrl_bytes = eval(self.getProperty("ctrlBytes"))

        self.get_energy_limits = self.getEnergyLimits
        if not self.chan_energy:
            self.energy_position_changed(self.default_en * 1000)

        self.get_wavelength_limits = self.getWavelengthLimits

    def can_move_energy(self):
        """Returns True if possible to change energy"""
        return self.tunable

    def isConnected(self):
        """Returns True if connected"""
        return True

    def isReady(self):
        """Returns always True"""
        return True

    def getCurrentEnergy(self):
        """Returns current energy in keV"""
        value = self.default_en
        if self.chan_energy is not None:
            try:
                value = self.chan_energy.getValue()
                return value[0]/1000
            except:
                logging.getLogger("HWR").exception(\
                       "Energy: could not read current energy")
                return None
        return value

    def getCurrentWavelength(self):
        """Returns current wavelength in A"""
        current_en = self.getCurrentEnergy()
        if current_en is not None:
            return (12.3984 / current_en)

    def getEnergyLimits(self):
        """Returns energy limits as list of two floats"""
        if (self.chan_limit_low is not None and \
            self.chan_limit_high is not None):
            try:
                self.limits[0] = self.chan_limit_low.getValue()
                self.limits[1] = self.chan_limit_high.getValue()
            except:
                logging.getLogger("HWR").exception("Energy: could not read energy limits")
        return self.limits

    def getWavelengthLimits(self):
        """Returns wavelength limits as list of two floats"""
        lims = None
        self.limits = self.getEnergyLimits()
        if self.limits is not None:
            lims = (12.3984 / self.limits[1], 12.3984 / self.en_lims[0])
        return lims

    def startMoveEnergy(self, value, wait=True):
        """Starts actual energy move"""
        try:
            value = float(value)
        except (TypeError, ValueError), diag:
            logging.getLogger('GUI').error(\
                  "Energy: invalid energy (%s)" % value)
            return False

        #current_en = self.getCurrentEnergy()
        """
        if current_en is not None:
            if math.fabs(value - current_en) < 0.001:
                self.moveEnergyCmdFinished(True)
        """
        if self.check_limits(value) is False:
            return False
        self.move_energy_started()
        def change_energy():
            try:
                self.move_energy(value, wait=True)
            except:
                self.move_energy_failed()
            #else:
            #    self.moveEnergyCmdFinished(True)
        if wait:
            change_energy()
        else:
            gevent.spawn(change_energy)

    def move_energy_started(self):
        self.emit('moveEnergyStarted', ())

    def move_energy_failed(self):
        self.moving = False
        self.emit('moveEnergyFailed', ())

    def move_energy_aborted(self):
        self.moving = False
        self.emit('moveEnergyFailed', ())

    def move_energy_finished(self, result):
        self.moving = False
        self.emit('moveEnergyFinished', ())

    def check_limits(self, value):
        """Checks given value if it is within limits"""
        logging.getLogger("HWR").info("Checking the move limits")
        if value >= self.limits[0] and value <= self.en_lims[1]:
            logging.getLogger("HWR").info("Limits ok")
            return True
        logging.getLogger("GUI").info("Requested value is out of limits")
        return False

    def start_move_wavelength(self, value, wait=True):
        logging.getLogger("HWR").info("Moving wavelength to (%s)" % value)
        return self.start_move_energy(12.3984/value, wait)
        #return self.startMoveEnergy(value, wait)

    def cancel_move_energy(self):
        logging.getLogger('user_level_log').info("Cancel move")
        #self.moveEnergy.abort()

    def move_energy(self, energy, wait=True):
        """In our case we set energy in keV"""
        current_en = self.getCurrentEnergy()
        pos = abs(current_en - energy)
        if pos < 0.001:
            self.emit('energyStateChanged', ('ready', ))
        else:
            logging.getLogger('GUI').info(\
                "Moving energy to %.3f", energy)
            if self.cmd_energy_ctrl_byte is not None:
                if pos > 0.1:
                    #p13 63, p14 15
                    self.cmd_energy_ctrl_byte(self.ctrl_bytes[1])
                else:
                    self.cmd_energy_ctrl_byte(self.ctrl_bytes[0])

            self.moving = True
            self.release_break_bragg()
            sleep(2)

            if self.cmd_set_energy:
                logging.getLogger('GUI').info("Moving energy to %.3f", energy)
                self.cmd_set_energy(energy)
            else:
                #Mockup mode
                self.energy_position_changed([energy * 1000])

    def move_wavelength(self, value, wait=True):
        self.move_energy(12.3984/value, wait)

    def energy_position_changed(self, pos):
        #self.moveEnergyCmdFinished(True)
        if type(pos) in (list, tuple):
            pos = pos[0]
        energy = pos / 1000
        if abs(energy - self.current_energy) > 1e-3:
            self.current_energy = energy
            self.current_wav = 12.3984 / energy
            if self.current_wav is not None:
                self.emit('energyChanged', (self.current_energy, self.current_wav))
                self.emit('valueChanged', (self.current_energy, ))

    def energy_limits_changed(self, limits):
        self.limits = self.getEnergyLimits()
        self.emit('energyLimitsChanged', (self.limits,))

    def energy_state_changed(self, state):
        state = int(state[0])
        if state == 0:
            if self.moving:
                self.set_break_bragg()
            self.move_energy_finished(0)
            self.emit('stateChanged', "ready")
        elif state == 1:
            self.move_energy_started()
            self.emit('stateChanged', "busy")
   
    def bragg_break_status_changed(self, status):
        self.bragg_break_status = status
        if status == 0:
            self.emit('statusInfoChanged', "Bragg brake set")
        if status == 1:
            self.emit('statusInfoChanged', "Bragg brake released")

    def get_value(self):
        return self.getCurrentEnergy()

    def update_values(self):
        self.emit('energyChanged', (self.current_energy, self.current_wav))
        self.emit('valueChanged', (self.current_energy, ))
        self.emit('energyLimitsChanged', self.limits)

        if self.bragg_break_status == 0:
            self.emit('statusInfoChanged', "Bragg brake set")
        if self.bragg_break_status == 1:
            self.emit('statusInfoChanged', "Bragg brake released")

    def undulator_gaps_changed(self, value):
        if type(value) in (list, tuple):
            self.undulator_gaps = [value[0]]
        else:
            self.undulator_gaps = [value]

    def get_undulator_gaps(self):
        if self.chan_undulator_gaps:
            self.undulator_gaps_changed(self.chan_undulator_gaps.getValue())
        return self.undulator_gaps

    def set_break_bragg(self):
        logging.getLogger('GUI').info("Setting bragg brake...")
        self.emit('statusInfoChanged', "Setting bragg brake...")
        self.cmd_set_break_bragg(1)
        sleep(5)
        with gevent.Timeout(15, Exception("Timeout waiting for break set")):
            while self.chan_status_bragg_break.getValue() != 0:
               gevent.sleep(0.1)
        #TODO status changes 0 -> 1 -> 0
        # so we wait again. this should be fixed in energy server or do some workaround here
        sleep(5) 
        if self.chan_status_bragg_break is not None:
            with gevent.Timeout(10, Exception("Timeout waiting for break set")):
                while self.bragg_break_status != 0:
                   sleep(0.01)
        else:
            sleep(10)
        logging.getLogger('GUI').info("Bragg brake set")

    def release_break_bragg(self):
        logging.getLogger('GUI').info("Releasing bragg brake...")
        self.emit('statusInfoChanged', "Releasing bragg brake...")
        self.cmd_release_break_bragg(1)
        sleep(2)
        if self.chan_status_bragg_break is not None:
            with gevent.Timeout(10, Exception("Timeout waiting for break release")):
                while self.bragg_break_status != 1:
                   sleep(0.01)
        else:
            sleep(10)
        logging.getLogger('GUI').info("Bragg brake released")

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
EMBLCRL
"""

import math
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLCRL(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)   

        self.current_energy = None
        self.crl_value = None
        self.chan_crl_value = None
        self.cmd_set_crl_value = None
        self.cmd_set_trans_value = None
        self.energy_hwobj = None
           
    def init(self):
        self.crl_value = 0

        self.chan_crl_value = self.getChannelObject('chanCrlValue')
        if self.chan_crl_value: 
            self.chan_crl_value.connectSignal('update', self.crl_value_changed)

        self.cmd_set_crl_value = self.getCommandObject('cmdSetLenses')
        self.cmd_set_trans_value = self.getCommandObject('cmdSetTrans')

        self.energy_hwobj = self.getObjectByRole("energy")
        if self.energy_hwobj:
            self.connect(self.energy_hwobj, 
                         "energyChanged", 
                         self.energy_changed)
 
    def energy_changed(self, energy_value, wavelength_value):
        self.current_energy = energy_value
        if self.crl_value:
            min_abs = 20
            selected_combination = None 

            for combination_index in range(64):
                current_abs = abs(self.current_energy - math.sqrt((2 * 341.52 * \
                    combination_index) / (2000 * (1 / 42.67 + 1 / 24.7))))
                if current_abs < min_abs:
                    min_abs = current_abs
                    selected_combination = combination_index

    def crl_value_changed(self, value):
        self.crl_value = value
        self.emit('crlValueChanged', self.crl_value)

    def set_crl_value(self, value):
        self.cmd_set_crl_value(value)
        self.cmd_set_trans_value(1) 

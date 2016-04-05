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
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        HardwareObject.__init__(self, name)   

        self.modes = None
        self.current_mode = None
        self.current_energy = None
        self.current_focusing_mode = None
        self.crl_value = None
        self.chan_crl_value = None
        self.cmd_set_crl_value = None
        self.cmd_set_trans_value = None

        self.energy_hwobj = None
        self.beam_focusing_hwobj = None
           
    def init(self):
        """
        Descript. :
        """
        self.modes = eval(self.getProperty("modes"))
        self.current_mode = self.getProperty("default_mode")

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
        self.beam_focusing_hwobj = self.getObjectByRole("beam_focusing")
        self.connect(self.beam_focusing_hwobj,
                     "focusingModeChanged",
                     self.focusing_mode_changed)

        self.current_focusing_mode, beam_size = self.beam_focusing_hwobj.\
             get_active_focus_mode()
        self.focusing_mode_changed(self.current_focusing_mode, beam_size)

    def get_modes(self):
        """
        Descript. :
        """
        return self.modes

    def get_mode(self):
        """
        Descript. :
        """
        return self.current_mode

    def set_mode(self, mode):
        """
        Descript. :
        """
        self.current_mode = mode  
        if self.current_mode == "Out":
            self.set_crl_value([0, 0, 0, 0, 0, 0])
        #elif self.current_mode == "Automatic":
        #    self.set_crl_value 
        self.emit('crlModeChanged', self.current_mode) 
 
    def energy_changed(self, energy_value, wavelength_value):
        """
        Descript. :
        """
        self.current_energy = energy_value
        self.crl_value = self.chan_crl_value.getValue()

        if self.current_mode == "Automatic":
            self.set_according_to_energy()


    def set_according_to_energy(self): 
        min_abs = 20
        selected_combination = None 
        crl_value = [0, 0, 0, 0, 0, 0]

        for combination_index in range(64):
            current_abs = abs(self.current_energy - math.sqrt((2 * 341.52 * \
                combination_index) / (2000 * (1 / 42.67 + 1 / 24.7))))
            if current_abs < min_abs:
                min_abs = current_abs
                selected_combination = combination_index
        crl_value = [int(x) for x in bin(selected_combination)[2:]]
        len_crl_value = len(crl_value) 
        if len_crl_value < 6:
           for index in range(6 - len_crl_value):
               crl_value.insert(0, 0) 
        self.ser_crl_value(crl_value)

    def focusing_mode_changed(self, focusing_mode, beam_size): 
        """
        Descript. :
        """
        self.current_focusing_mode = focusing_mode
        self.crl_value = self.beam_focusing_hwobj.get_lens_combination()
        self.set_crl_value(self.crl_value)
        self.current_mode = "Manual"     
        self.emit('crlModeChanged', self.current_mode)

    def crl_value_changed(self, value):
        """
        Descript. :
        """
        self.crl_value = value
        self.emit('crlValueChanged', self.crl_value)

    def set_crl_value(self, value):
        """
        Descript. :
        """
        if value is not None:
           self.cmd_set_crl_value(value)
           self.cmd_set_trans_value(1)

    def update_values(self):
        """
        Descript. :
        """
        self.emit('crlModeChanged', self.current_mode)
        self.emit('crlValueChanged', self.crl_value)

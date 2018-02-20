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

import logging
from random import random
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3."
__category__ = "General"


class FluxMockup(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.flux_value = None
        self.flux_info = {}
        self.beam_info = None
        self.transmission = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
   
        self.flux_value = 1
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.connect(self.beam_info_hwobj,
                     "beamInfoChanged",
                     self.beam_info_changed)
        self.beam_info_changed(self.beam_info_hwobj.get_beam_info())

        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.connect(self.transmission_hwobj,
                     "attFactorChanged",
                     self.transmission_changed)
        self.transmission_changed(self.transmission_hwobj.getAttFactor())

    def beam_info_changed(self, beam_info):
        self.beam_info = beam_info
        #self.update_flux_value()

    def transmission_changed(self, transmission):
        self.transmission = transmission
        #self.update_flux_value()

    def set_flux(self, flux_value):
        self.flux_value = flux_value
        #self.origin_flux_value = copy(flux_value)
        #self.origin_beam_info = copy(self.beam_info)
        #self.origin_transmission = copy(self.transmission)
        self.update_flux_value()

    def get_flux(self):
        return self.flux_value

    def get_flux_info(self):
        return self.flux_info

    def update_flux_value(self):
        self.flux_info = {"flux" : self.flux_value,
                          "beam_info": self.beam_info,
                          "transmission": self.transmission}
        self.emit('fluxChanged', self.flux_info)
        """
        if self.flux_value is not None:
            if self.origin_transmission is not None:
                if self.origin_transmission != self.transmission:
                    self.flux_value = self.origin_flux_value * self.transmission / \
                                      self.origin_transmission
                else:
                    self.flux_value = self.origin_flux_value
            if self.origin_beam_info is not None:
                if self.origin_beam_info != self.beam_info:
                    if self.origin_beam_info['shape'] == 'ellipse':
                        origin_area = 3.141592 * pow(self.origin_beam_info['size_x'] / 2, 2)
                    else:     
                        origin_area = self.origin_beam_info['size_x'] * \
                                      self.origin_beam_info['size_y']

                    if self.beam_info['shape'] == 'ellipse':
                        current_area = 3.141592 * pow(self.beam_info['size_x'] / 2, 2)
                    else:
                        current_area = self.beam_info['size_x'] * \
                                       self.beam_info['size_y']
                    self.flux_value = self.flux_value * current_area / \
                                      origin_area   
            self.emit('fluxChanged', self.flux_value, self.beam_info, self.transmission)
        """

    def measure_intensity(self):
        """Measures intesity"""
        self.flux_value = 1e+12 + random() * 1e+12
        self.update_flux_value() 

    def update_values(self):
        self.emit('fluxChanged', self.flux_info)

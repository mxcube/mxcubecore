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

from random import random
from HardwareRepository.HardwareObjects.abstract.AbstractFlux import AbstractFlux


__credits__ = ["MXCuBE collaboration"]
__category__ = "General"


class FluxMockup(AbstractFlux):
    def __init__(self, name):
        AbstractFlux.__init__(self, name)

        self.beam_info_hwobj = None
        self.transmission_hwobj = None

        self.measured_flux_list = []
        self.measured_flux_dict = {}
        self.current_flux_dict = {}

    def init(self):
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.transmission_hwobj = self.getObjectByRole("transmission")

        self.measure_flux()  

    def get_flux(self):
        return self.current_flux_dict["flux"]

    def measure_flux(self):
        """Measures intesity"""
        beam_size = self.beam_info_hwobj.get_beam_size()
        transmission = self.transmission_hwobj.getAttFactor()
        flux = 1e12 + random() * 1e12

        self.measured_flux_list = [{"size_x": beam_size[0],
                                    "size_y": beam_size[1],
                                    "transmission": transmission,
                                    "flux": flux}]

        self.measured_flux_dict = self.measured_flux_list[0]
        self.current_flux_dict = self.measured_flux_list[0]

        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )

    def get_flux_info_list(self):
        return self.measured_flux_list

    def set_flux_info_list(self, flux_info_list):
        self.measured_flux_list = flux_info_list
        self.measured_flux_dict = self.measured_flux_list[0]
        #TODO Adjust to beamsize and transmission
        self.current_flux_dict = self.measured_flux_list[0]
        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )
        
          

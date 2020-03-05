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

from HardwareRepository import HardwareRepository as HWR

__credits__ = ["MXCuBE collaboration"]
__category__ = "General"


class FluxMockup(AbstractFlux):

    # default_flux - for initialising mockup
    default_flux = 1e10

    def __init__(self, name):
        AbstractFlux.__init__(self, name)

        self.measured_flux_list = []
        self.measured_flux_dict = {}
        self.current_flux_dict = {}

    def get_flux(self):
        """Get flux at current transmission in units of photons/s"""
        self.measure_flux()
        return self.current_flux_dict["flux"]

    def measure_flux(self):
        """Measures intesity"""
        beam_size_hor, beam_size_ver = HWR.beamline.beam.get_size()
        transmission = HWR.beamline.transmission.get_value()
        flux = self.default_flux * (1 + random())

        self.measured_flux_list = [{"size_x": beam_size_hor,
                                    "size_y": beam_size_ver,
                                    "transmission": transmission,
                                    "flux": flux}]

        self.measured_flux_dict = self.measured_flux_list[0]
        self.current_flux_dict = self.measured_flux_list[0]

        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )

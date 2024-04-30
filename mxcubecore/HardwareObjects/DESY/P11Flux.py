#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from random import random
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux

from mxcubecore import HardwareRepository as HWR

__credits__ = ["MXCuBE collaboration"]
__category__ = "General"


class P11Flux(AbstractFlux):

    # default_flux - for initialising mockup
    default_flux = 5e12

    def __init__(self, name):
        AbstractFlux.__init__(self, name)

        self.measured_flux_list = []
        self.measured_flux_dict = {}
        self.current_flux_dict = {}

    def init(self):

        self.measure_flux()

    def get_value(self):
        """Get flux at current transmission in units of photons/s"""

        """ FLUX IS CHEETED HERE - NOWERE ELSE!"""
        return self.current_flux_dict["flux"]

    def measure_flux(self):
        """Measures intesity"""
        beam_size = HWR.beamline.beam.get_beam_size()
        transmission = HWR.beamline.transmission.get_value()
        flux = self.default_flux * (1 + random())

        self.measured_flux_list = [
            {
                "size_x": beam_size[0],
                "size_y": beam_size[1],
                "transmission": transmission,
                "flux": flux,
            }
        ]

        self.measured_flux_dict = self.measured_flux_list[0]
        self.current_flux_dict = self.measured_flux_list[0]

        self.emit(
            "fluxInfoChanged",
            {"measured": self.measured_flux_dict, "current": self.current_flux_dict},
        )

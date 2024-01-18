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

"""
Mock-up class to simulate the beamline flux, used for testing.
"""

from random import random
from gevent import sleep, Timeout
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux

from mxcubecore import HardwareRepository as HWR


__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class FluxMockup(AbstractFlux):
    """Class to simulate beamline flux"""

    def __init__(self, name):
        super().__init__(name)

        self.measured_flux_list = []
        self.measured_flux_dict = {}
        self.current_flux_dict = {}

    def init(self):
        super().init()
        self.current_flux_dict["flux"] = self.default_value

    def get_value(self):
        """Get flux at current transmission in units of photons/s"""
        self.measure_flux()
        return self.current_flux_dict["flux"]

    def measure_flux(self) -> None:
        """
        Measures intesity

        Emits:
           valueChanged (float): The new flux value
        """
        beam_size = HWR.beamline.beam.get_beam_size()
        transmission = HWR.beamline.transmission.get_value()
        flux = self.default_value * (1 + 0.001 * random()) * transmission / 100.0

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

        self.emit("valueChanged", self.current_flux_dict["flux"])

    @property
    def is_beam(self):
        """Check if there is beam
        Returns:
            (bool): True if beam present, False otherwise
        """
        return True

    def wait_for_beam(self, timeout=None):
        """Wait until beam present
        Args:
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                                              (default);
                             if timeout is None: wait forever.
        """
        with Timeout(timeout, RuntimeError("Timeout while waiting for beam")):
            sleep(timeout + 1)

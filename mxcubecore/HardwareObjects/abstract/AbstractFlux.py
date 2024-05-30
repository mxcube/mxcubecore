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

"""AbstractFlux class
Defines get_average_flux_density.
"""
from scipy.interpolate import interp1d

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator

from mxcubecore import HardwareRepository as HWR

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractFlux(AbstractActuator):
    """Class for Flux abstraction"""

    def __init__(self, name):
        super().__init__(name)
        # flux by default is read only
        self.read_only = True

    def init(self):
        """Initialise some parameters."""
        super().init()
        self.read_only = self.get_property("read_only") or True

    # Dose rate for a standard composition crystal, in Gy/s
    # As a function of energy in keV
    #
    # NB this can be called as a function, the same as if it was defined thus:
    # def get_dose_rate_per_photon_per_mmsq(self, energy):
    #
    # The interpolation table get_dose_rate_per_photon_per_mmsq was created using
    # "Absorbed dose calculations for macromolecular crystals: improvements to RADDOSE"
    # Paithankar, K.S., Owen, R.L and Garman, E.F J. Syn. Rad. (2009), 16, 152-162,
    # for some sensible crystal composition, by Gleb Bourenkov
    #
    # The reason for *not* having a get_dose_rate function is that the actual dose rate
    # depends heavily on beam profile and crystal size and shape.
    # The necessary approximations should be done locally.
    # See GphlWorkflow for an example of how to do it.
    #
    get_dose_rate_per_photon_per_mmsq = interp1d(
        [4.0, 6.6, 9.2, 11.8, 14.4, 17.0, 19.6, 22.2, 24.8, 27.4, 30.0],
        [
            4590.0e-12,
            1620.0e-12,
            790.0e-12,
            457.0e-12,
            293.0e-12,
            202.0e-12,
            146.0e-12,
            111.0e-12,
            86.1e-12,
            68.7e-12,
            55.2e-12,
        ],
    )

    def get_average_flux_density(self, transmission=None):
        """Get average flux density over the beam area in photons / mm^2
        for a given transmisison setting
        Args:
            transmission (float): Target transmission [%]
                                  (defaults to current value)
        Returns:
            (float): (photons / mm^2) - average flux density over beam area.
        """
        beam_size = HWR.beamline.beam.get_beam_size()
        flux = self.get_value()
        result = None
        if flux and all(beam_size):
            result = flux / (beam_size[0] * beam_size[1])
            if transmission is not None:
                result *= transmission / HWR.beamline.transmission.get_value()
        return result

# encoding: utf-8
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

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import numpy as np
from scipy.interpolate import (
    Rbf,
    interp1d,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux

__credits__ = ["MXCuBE collaboration"]
__category__ = "General"


class P11Flux(AbstractFlux):
    def __init__(self, name):
        super().__init__(name)

        self.measured_flux_list = []
        self.measured_flux_dict = {}
        self.current_flux_dict = {}

    def init(self):
        # Here are reference flux values from the config file
        # Those are values at which flux is measured
        self.default_flux = self.get_property("defaultFlux")

        self.default_beamsize = self.get_property("defaultBeamsize")
        self.default_pinhole = self.get_property("defaultPinhole")
        self.default_energy = self.get_property("defaultEnergy")
        self.default_current = self.get_property("defaultCurrent")
        self.measure_flux()

    def get_value(self):
        """Get flux at current transmission in units of photons/s"""
        # TODO: Once the motor movements are involved, check the logic.
        self.measure_flux()
        return self.current_flux_dict["flux"]

    def measure_flux(self):
        """Measures intesity"""
        beam_size = HWR.beamline.beam.get_beam_size()
        transmission = HWR.beamline.transmission.get_value()
        energy = HWR.beamline.energy.get_value() * 1000
        # TODO: Check pinhole from HWR.beamline.diffractometer
        current_pinhole = HWR.beamline.beam.get_pinhole_size()
        current = HWR.beamline.machine_info.get_current()
        mess = HWR.beamline.machine_info.get_message()

        flux = (
            self.estimate_flux_with_reference(
                max(beam_size[0] * 1000, beam_size[0] * 1000),
                max(beam_size[0] * 1000, beam_size[0] * 1000),
                energy,
                current,
                self.default_beamsize,
                self.default_pinhole,
                self.default_energy,
                self.default_flux,
                self.default_current,
            )
            * transmission
            / 100.0
        )

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

        self.log.debug(
            f"Estimated flux for beam size {max(beam_size[0] * 1000, beam_size[0] * 1000)}, pinhole size {current_pinhole}, transmission {transmission}, energy {energy} eV and current {current} mA: {flux:.2e} ph/s"
        )

    def estimate_flux_with_reference(
        self,
        beam_size,
        pinhole_size,
        energy,
        current,
        ref_beam_size,
        ref_pinhole_size,
        ref_energy,
        ref_flux,
        ref_current,
    ):
        """
        Helper function to estimate the flux based on the input beam size, pinhole size, energy, and current, scaled by a reference flux and current.
        Temporary plug to have realistic flux estimations.

        Parameters:
        beam_size (int): Beam size in numerical format (e.g., 300, 200, 100, 50, 20, 9)
        pinhole_size (int): Pinhole size in numerical format (e.g., 200, 100, 50, 20)
        energy (int): Energy in eV
        current (float): Current in mA
        ref_beam_size (int): Reference beam size
        ref_pinhole_size (int): Reference pinhole size
        ref_energy (int): Reference energy in eV
        ref_flux (float): Reference flux value
        ref_current (float): Reference current in mA

        Returns:
        float: Estimated flux
        """
        # Measured table at different beam parameters
        beam_sizes = np.array([300, 300, 300, 300, 200, 100, 50, 20, 9])
        pinhole_sizes = np.array([200, 100, 50, 20, 200, 200, 200, 200, 100])
        fluxes = np.array(
            [2e12, 5e11, 1.25e11, 2e10, 4.4e12, 9.9e12, 9.9e12, 9.9e12, 8.7e12]
        )
        energies = np.full(beam_sizes.shape, 12000)

        # Measured energy-flux dependance
        energy_flux = np.array(
            [
                [6000, 1.70e12],
                [7000, 3.70e12],
                [8000, 4.90e12],
                [10000, 3.90e12],
                [12000, 4.37e12],
                [14000, 4.20e12],
                [16000, 3.80e12],
                [18000, 3.00e12],
                [20000, 2.20e12],
                [22000, 1.60e12],
                [24000, 9.10e11],
                [26000, 5.80e11],
            ]
        )

        X = np.column_stack((beam_sizes, pinhole_sizes, energies))
        y = fluxes
        rbf_interpolator = Rbf(X[:, 0], X[:, 1], X[:, 2], y, function="linear")
        energy_flux_interpolator = interp1d(
            energy_flux[:, 0],
            energy_flux[:, 1],
            kind="linear",
            fill_value="extrapolate",
        )
        estimated_ref_flux = rbf_interpolator(
            ref_beam_size, ref_pinhole_size, ref_energy
        )

        if np.isnan(estimated_ref_flux):
            raise RuntimaWarning(
                "Reference flux cannot be estimated using the interpolator. Check reference points."
            )

        # Scale the flux based on the reference flux
        scale_factor = ref_flux / estimated_ref_flux

        # Estimate the flux at the desired beam, pinhole size, and energy
        estimated_flux = rbf_interpolator(
            beam_size, pinhole_size, 12000
        )  # Always interpolate at 12000 eV

        if np.isnan(estimated_flux):
            raise RuntimaWarning(
                "Desired flux cannot be estimated using the interpolator. Check input points."
            )

        # Scale the estimated flux based on the energy-dependent flux variation
        energy_scale_factor = energy_flux_interpolator(
            energy
        ) / energy_flux_interpolator(
            12000
        )  # Scaling relative to 12000 eV

        # Scale the flux based on the current
        current_scale_factor = current / ref_current

        return (
            estimated_flux * scale_factor * energy_scale_factor * current_scale_factor
        )

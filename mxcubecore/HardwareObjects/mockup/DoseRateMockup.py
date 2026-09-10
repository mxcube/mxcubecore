# encoding: utf-8
#
#  Project name: MXCuBE
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
"""Radiation dose mock object"""

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

from random import uniform

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.DoseRate import DoseRate


class DoseRateMockup(DoseRate):
    """DoseRate mock class"""

    def calculate_dose(self, flux: float | None = None) -> float:
        """Calculate the dose rate as function of the flux value.
        Args:
            flux: Flux value.
        Returns:
            The calculated dose [MGy/s]
        """
        if flux is None:
            flux = HWR.beamline.flux.get_value()
        if flux > 0:
            return flux * uniform(0, 300.0) / 1e12  # noqa S311
        return 0

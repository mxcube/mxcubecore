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
"""Radiation dose for a sample as function of the flux. Uses the beamline.flux
The dose calculation routine has to be provided externally.
Example yml configuration:

.. code-block:: yaml

 class: DoseRate.DoseRate
   configuration:
      actuator_name: doserate
      username: Radiation Dose Rate
      read_only: True
      default_limits: (0,500)  # MGy/s
   objects:
      dose_calculator: dose_calculator.yaml

"""

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"


from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


class DoseRate(AbstractActuator):
    """Report the dose rate"""

    unit = "MGy/s"

    def __init__(self, name):
        super().__init__(name)
        self.dose_calc = None

    def init(self):
        """Initialisation"""
        super().init()
        self.dose_calc = self.get_object_by_role("dose_calculator")
        try:
            HWR.beamline.flux.connect("valueChanged", self.update_value)
        except AttributeError as err:
            raise RuntimeError("Flux reading is not configured") from err

    def get_value(self) -> float:
        """Get the dose rate value as function of the photon flux.
        Returns:
            dose rate [MGy/s]
        """
        self._nominal_value = self.calculate_dose(HWR.beamline.flux.get_value())
        return self._nominal_value

    def calculate_dose(self, flux: float | None = None) -> float:
        """Calculate the dose rate as function of the flux value.
        Args:
            flux: Flux value. If None, read the current beamline flux.
        Returns:
            The calculated dose [MGy/s]
        """
        if flux is None:
            flux = HWR.beamline.flux.get_value()
        if flux > 0:
            return self.dose_calc(flux)
        return 0

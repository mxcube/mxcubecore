# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""
MicrodiffAperture

Example xml file:
<object class="MicrodiffAperture">
  <username>aperture</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <value_channel_name>CurrentApertureDiameterIndex</value_channel_name>
  <state_channel_name>State</state_channel_name>
  <-- either only factor -->
  <factor>(0.15, 0.3, 0.63, 0.9, 0.96)</factor>
  <!-- or complete, corresponding to label: (index, size[mm], factor) -->
  <values>{"A10": (0, 10, 0.15), "A20": (1, 20, 0.3), "A30": (2, 30, 0.63), "A50": (3, 50, 0.9), "A75": (4, 75, 0.96)}</values>
</object>
"""
from ast import literal_eval
from enum import Enum
from HardwareRepository.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from HardwareRepository.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffAperture(ExporterNState):
    """MicrodiffAperture class"""

    unit = "mm"

    def __init__(self, name):
        ExporterNState.__init__(self, name)

    def init(self):
        """Initialize the aperture"""
        ExporterNState.init(self)

        self.initialise_values()
        # check if we have values other that UKNOWN (no values in config)
        if len(self.VALUES) == 1:
            self._initialise_values()

    def _initialise_values(self):
        """Initialise the ValueEnum from the hardware
        Raises:
            RuntimeError: No aperture diameters defined.
                          Factor and aperture diameter not the same number.
                          Invalid factor values.
        """
        predefined_postions = self._exporter.read_property("ApertureDiameters")
        if not predefined_postions:
            raise RuntimeError("No aperture diameters defined")

        values = {}
        try:
            # get the factors
            factor = literal_eval(self.getProperty("factor"))
            if len(predefined_postions) == len(factor):
                for _pos, _fac in zip(predefined_postions, factor):
                    values["A{0}".format(_pos)] = (
                        predefined_postions.index(_pos),
                        _pos,
                        _fac,
                    )
            else:
                raise RuntimeError("Factor and aperture diameter not the same number")
        except (ValueError, TypeError):
            raise RuntimeError("Invalid factor values")

        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def get_factor(self, label):
        """ Get the factor associated to a label.
        Args:
            (enum, str): label enum or name
        Returns:
            (float): Factor value
        """
        if isinstance(label, str):
            try:
                return float(self.VALUES[label].value[2])
            except (KeyError, ValueError, IndexError):
                return 1.0
        try:
            return float(label.value[2])
        except (ValueError, IndexError):
            return 1.0

    def get_size(self, label):
        """ Get the aperture size associated to a label.
        Args:
            (enum, str): label enum or name
        Returns:
            (float): Factor value
        Raises:
            RuntimeError: Unknown aperture size.
        """
        if isinstance(label, str):
            try:
                return float(self.VALUES[label].value[1])
            except (KeyError, ValueError, IndexError):
                raise RuntimeError("Unknown aperture size")
        try:
            return float(label.value[1])
        except (ValueError, IndexError):
            raise RuntimeError("Unknown aperture size")

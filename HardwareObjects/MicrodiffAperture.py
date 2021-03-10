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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""
MicrodiffAperture. Move the aperture in the beam to a specified value or
out of the beam.

Example xml file:
<object class="MicrodiffAperture">
  <username>aperture</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <value_channel_name>CurrentApertureDiameterIndex</value_channel_name>
  <state_channel_name>State</state_channel_name>
  <-- either only factor -->
  <factor>(0.15, 0.3, 0.63, 0.9, 0.96)</factor>
  <!-- or complete, corresponding to label: (index, size[um], factor) -->
  <values>{"A10": (0, 10, 0.15), "A20": (1, 20, 0.3), "A30": (2, 30, 0.63), "A50": (3, 50, 0.9), "A75": (4, 75, 0.96)}</values>
  <object role="inout" href="/udiff_apertureinout"/>
</object>
"""
from ast import literal_eval
from enum import Enum
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffAperture(ExporterNState):
    """MicrodiffAperture class"""

    unit = "um"

    def __init__(self, name):
        super(MicrodiffAperture, self).__init__(name)
        self.inout_obj = None

    def init(self):
        """Initialize the aperture"""
        super(MicrodiffAperture, self).init()

        # check if we have values other that UKNOWN (no values in config)
        if len(self.VALUES) == 1:
            self._initialise_values()

        # now get the IN/OUT object
        self.inout_obj = self.get_object_by_role("inout")
        if self.inout_obj:
            self._initialise_inout()

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        if value.name in ("IN", "OUT"):
            _e = self.inout_obj.value_to_enum(value.value)
            self.inout_obj.set_value(_e, timeout=60)
        else:
            super(MicrodiffAperture, self)._set_value(value)

    def _initialise_inout(self):
        """Add IN and OUT to the values Enum"""
        values_dict = {item.name: item.value for item in self.inout_obj.VALUES}
        values_dict.update({item.name: item.value for item in self.VALUES})
        self.VALUES = Enum("ValueEnum", values_dict)

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
            factor = literal_eval(self.get_property("factor"))
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

    def get_diameter_size_list(self):
        values = []
        for value in self.VALUES:
            _n = value.name

            if _n in ["IN", "OUT"]:
                values.append(_n)
            elif _n not in ["UNKNOWN"]:
                values.append(_n[1:])

        return values

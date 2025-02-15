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
Example xml_ configuration:

.. code-block:: xml

 <object class="ApertureMockup">
   <username>aperture</username>
   <values>{"A5": (5, 0.11), A10": (10, 0.15), "A20": (20, 0.3), "A30": (30, 0.63), "A50": (50, 0.9), "A100": (100, 1)}</values>
   <position_list>["BEAM", "OFF", "PARK"]</position_list>
 </object>
"""

from enum import Enum

from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ApertureMockup(AbstractNState, ActuatorMockup):
    """Mockup file for aperture as Nstate actuator"""

    def init(self):
        super().init()
        # check if we have values other that UKNOWN (no values in config)
        if len(self.VALUES) == 1:
            self._initialise_values()
            self._initialise_inout()
        self._nominal_value = self.VALUES.A10

    def get_value(self):
        return self._nominal_value

    def _initialise_values(self):
        """Initialise the ValueEnum if not in the config"""
        values = {}
        predefined_postions = (5, 10, 20, 30, 50, 100)
        factors = (0.11, 0.15, 0.3, 0.63, 0.9, 1)
        for _pos, _fac in zip(predefined_postions, factors):
            values[f"A{_pos}"] = (_pos, _fac)
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in self.VALUES}),
        )

    def _initialise_inout(self):
        """Add IN and OUT to the values Enum"""
        values_dict = {"IN": "BEAM", "OUT": "OFF"}
        values_dict.update({item.name: item.value for item in self.VALUES})
        self.VALUES = Enum("ValueEnum", values_dict)

    def get_factor(self, label):
        """Get the factor associated to a label.
        Args:
            (enum, str): label enum or name
        Returns:
            (float) or (tuple): Factor value
        """
        if isinstance(label, str):
            try:
                return self.VALUES[label].value[1]
            except (KeyError, ValueError, IndexError):
                return 1.0
        try:
            return label.value[1]
        except (ValueError, IndexError):
            return 1.0

    def get_size(self, label):
        """Get the aperture size associated to a label.
        Args:
            (enum, str): label enum or name
        Returns:
            (float): Factor value
        Raises:
            RuntimeError: Unknown aperture size.
        """
        if isinstance(label, str):
            try:
                return float(self.VALUES[label].value[0])
            except (KeyError, ValueError, IndexError) as err:
                raise RuntimeError("Unknown aperture size") from err
        try:
            return float(label.value[0])
        except (ValueError, IndexError) as err:
            if self.inout_obj:
                return None
            raise RuntimeError("Unknown aperture size") from err

    def get_diameter_size_list(self):
        """Get the list of values to be visible. Hide IN, OUT and UNKNOWN.
        Returns:
            (list): List of availble aperture values (string).
        """
        values = []
        for value in self.VALUES:
            _nam = value.name

            if _nam not in ["IN", "OUT", "UNKNOWN"]:
                values.append(_nam)

        return values

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

"""
BeamDefinerMockup class.
Two mock motors change the width and the heigth of the beam.
Example xml configuration:

.. code-block:: xml

 <object class="BeamDefinerMockup">
   <username>Beam Definer</username>
   <object hwrid="/beam_size_ver" role="beam_size_ver" />
   <object hwrid="/beam_size_hor" role="beam_size_hor" />
   <values>{"50x50": (0.05, 0.05), "100x100": (0.1, 0.1), "20x5": (0.02, 0.005)}</values>
   <default_size_name>50x50</default_size_name>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

import random
import time

from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.mockup.ActuatorMockup import ActuatorMockup


class BeamDefinerMockup(AbstractNState, ActuatorMockup):
    """BeamDefinerMockup class"""

    def __init__(self, *args):
        super().__init__(*args)
        self.beam_size_hor = None
        self.beam_size_ver = None

    def init(self):
        super().init()
        self.beam_size_hor = self.get_object_by_role("beam_size_hor")
        self.beam_size_ver = self.get_object_by_role("beam_size_ver")

        # set default value [mm]
        self.beam_size_hor.set_value(0.1)
        self.beam_size_ver.set_value(0.1)

        _default_name = self.get_property("default_size_name")
        if self.get_value() == self.VALUES.UNKNOWN and _default_name:
            # set default beam value
            self._set_value(self.VALUES[_default_name])
        self.update_value()

        self.connect(self.beam_size_hor, "valueChanged", self.motors_changed)
        self.connect(self.beam_size_ver, "valueChanged", self.motors_changed)

    def motors_changed(self, value):
        """Emit valueChanged for the definer when motor position changed"""
        print(value)
        name = self.get_current_position_name()
        self.emit("valueChanged", name)

    def get_value(self):
        """Get the beam value.
        Returns:
            (Enum): The current position Enum.
        """
        try:
            return self.VALUES[self.get_current_position_name()]
        except (ValueError, KeyError, TypeError):
            return self.VALUES.UNKNOWN

    def get_current_position_name(self):
        """Get the current beam size name.
        Returns:
            (str): Current beam size name.
        """
        hor = self.beam_size_hor.get_value()
        ver = self.beam_size_ver.get_value()
        for val in self.VALUES:
            if val.value == (hor, ver):
                return val.name
        return "UNKNOWN"

    def _set_value(self, value):
        """Set the beam size.
        Args:
            value(str): name of the beam size to set.
        """
        if isinstance(value, str):
            size_x, size_y = self.VALUES[value].value
        else:
            size_x, size_y = value.value
        self.beam_size_hor.set_value(float(size_x))
        self.beam_size_ver.set_value(float(size_y))
        time.sleep(random.uniform(0.3, 1.0))
        self.update_value(value)

    def get_predefined_positions_list(self):
        """Get the position labels list.
        Returns:
            (list): List of all the labels defined.
        """
        values = []
        for value in self.VALUES:
            nam = value.name
            if value.name != "UNKNOWN":
                values.append(nam)
        return values

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
Generic ESRF Beam Definer.

Example xml configuration:

.. code-block:: xml

 <object class="ESRF.ESRFBeamDefiner"
   <username>Beam Definer</username>
   <beam_config>
      <name>4x4 um</name>
      <beam_size>0.004, 0.004</beam_size>
   </beam_config>
   <beam_config>
      <name>4x8 um</name>
      <beam_size>0.004, 0.008</beam_size>
   </beam_config>
   <default_size_name>4x4 um</default_size_name>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

from ast import literal_eval
from enum import Enum
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState


class ESRFBeamDefiner(AbstractNState):
    """Generic ESRF beam definer implementation"""

    def __init__(self, *args):
        super().__init__(*args)
        self.beam_config = {}
        self.config = []

    def init(self):
        super().init()
        self._default_name = self.get_property("default_size_name")

        # keep the config is needed by the inheriring classes
        self.config = self.init_config()

        # check if we have values other that UKNOWN
        if len(self.VALUES) == 1:
            self._initialise_values()

    def init_config(self):
        """Get the configutarion from the file"""

        cfg = self["beam_config"]
        if not isinstance(cfg, list):
            cfg = [cfg]

        for beam_cfg in cfg:
            name = beam_cfg.get_property("name")
            beam_size = beam_cfg.get_property("beam_size", (0.015, 0.015))
            if isinstance(beam_size, str):
                beam_size = literal_eval(beam_size)
                self.beam_config.update({name: beam_size})
        return cfg

    def get_limits(self):
        return (1, len(self.beam_config))

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): The current position Enum.
        """
        try:
            return self.VALUES[self.get_current_position_name()]
        except (ValueError, KeyError):
            return self.VALUES.UNKNOWN

    def get_size(self):
        """Get the current beam size (horozontal and vertical).
        Returns:
            (tuple): Curren beam size (horizontal, vertical) [mm].
        """
        return self.get_value().value

    def get_current_position_name(self):
        """Get the current beam size name.
        Returns:
            (str): Current beam size name.
        """
        raise NotImplementedError

    def get_predefined_positions_list(self):
        """Get the list of all the beam size names.
        Returns:
            (list): List of strings with the beam size names.
        """
        return list(self.beam_config.keys())

    def _initialise_values(self):
        """Initialise the ValueEnum from the configuration.
        Raises:
            RuntimeError: No values defined.
        """
        self.VALUES = Enum(
            "ValueEnum",
            dict(self.beam_config, **{item.name: item.value for item in self.VALUES}),
        )

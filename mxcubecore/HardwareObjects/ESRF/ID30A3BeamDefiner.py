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
ID30-A3 Beam Definer.

Example xml configuration:

.. code-block:: xml

 <object class="ESRF.ID30A3BeamDefiner"
   <object href="/udiff_aperture" role="controller"/>
   <beam_config>
      <name>15um, A15 um</name>
      <beam_size>0.015, 0.015</beam_size>
      <aperture_size>15</aperture_size>
   </beam_config>
   <beam_config>
      <name>15um, A15 um</name>
      <beam_size>0.015, 0.015</beam_size>
      <aperture_size>30</aperture_size>
   </beam_config>
   <beam_config>
      <name>7um, A7 um</name>
      <beam_size>0.007, 0.007</beam_size>
      <aperture_size>7</aperture_size>
   </beam_config>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

from enum import Enum

from mxcubecore.HardwareObjects.ESRF.ESRFBeamDefiner import ESRFBeamDefiner


class ID30A3BeamDefiner(ESRFBeamDefiner):
    """ID30-A3 beam definer implementattion"""

    def __init__(self, *args):
        super().__init__(*args)
        self.controller = None

    def init(self):
        """Initialisation"""
        super().init()

        self.controller = self.get_object_by_role("controller")
        _dict = {}
        for beam_cfg in self.config:
            name = beam_cfg.get_property("name")
            _ap_size = beam_cfg.get_property("aperture_size")
            _aperture = self.controller.value_to_enum(_ap_size, idx=1)
            _dict[name] = [self.beam_config[name], _aperture]

        self.beam_config = _dict
        self._initialise_values()
        self.connect(self.controller, "valueChanged", self._update_name)

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        return self.controller.get_state()

    def _update_name(self, value=None):
        """
        Emits:
            valueChanged (str): Current beam size name.
        """
        name = self.get_current_position_name()
        self.emit("valueChanged", name)

    def get_current_position_name(self):
        """Get the current beam size name.
        Returns:
            (str): Current beam size name.
        """
        _aperture = self.controller.get_value()
        for name in self.beam_config:
            if self.beam_config[name][1] == _aperture:
                return name
        return "UNKNOWN"

    def get_value(self):
        """Get the device value
        Returns:
            (Enum): The current position Enum.
        """
        try:
            value = self.VALUES[self.get_current_position_name()]
            if isinstance(value.value, tuple):
                return value
            return Enum("Dummy", {value.name: value.value[0]})[value.name]
        except (ValueError, KeyError):
            return self.VALUES.UNKNOWN

    def set_value(self, value, timeout=None):
        """Set the beam size.
        Args:
            value(str): name of the beam size to set.
            timeout(float): Timeout to wait for the execution to finish [s].
        Raises:
            RuntimeError: Cannot change beam size.
        """
        if isinstance(value, Enum):
            value = value.name

        self.controller.set_value(self.beam_config[value][1], timeout=timeout)

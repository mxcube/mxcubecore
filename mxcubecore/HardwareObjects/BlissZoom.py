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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Configure pixel/mm, light level and other parameters (if needed) for every
zoom level. The zoom motor is a bliss motor, but we use it as an NState.

Example xml configuration:

.. code-block:: xml

 <object class="BlissZoom"
   <username>Zoom</username>
   <zoom_config>
      <name>LEVEL1</name>
      <position>1</position>
      <pixels_per_mm_x>354</pixels_per_mm_x>
      <pixels_per_mm_y>354</pixels_per_mm_y>
      <!-- optional -->
      <light_level>0.26</light_level>
   </zoom_config>
   <zoom_config>
   ...
   </zoom_config>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.BlissNState import BlissNState


class BlissZoom(BlissNState):
    def __init__(self, name):
        super().__init__(name)
        self.zoom_config = {}

    def init(self):
        super().init()
        cfg = self.get_property("zoom_config")
        for _cfg in cfg:
            self.zoom_config[_cfg.pop("name")] = _cfg
        self.get_calibration()

    def get_light_level(self):
        """Get the light level"""
        name = self.get_value().name
        return self.zoom_config[name].get("light_level")

    def set_light_level(self, value):
        """Set the backlight light level.
        Args:
           value (str or enum): target value
        """
        light = HWR.beamline.diffractometer.motors_hwobj_dict.get("backlight")
        if light:
            light.set_value(value, timeout=0)

    def get_calibration(self) -> tuple[int, int]:
        """Get the pixel/mm values.

        Returns:
            (x ,y) [pixel/mm]
        """
        name = self.get_value().name
        _pmx = self.zoom_config[name].get("pixels_per_mm_x")
        _pmy = self.zoom_config[name].get("pixels_per_mm_y")

        if all([_pmx, _pmy]):
            return _pmx, _pmy
        msg = "Zoom not calibrated"
        raise RuntimeError(msg)

    def _set_value(self, value):
        """Set the zoom to value. Set the backlight light level, if defined.
        Args:
            value: target value
        """
        super()._set_value(value)
        level = self.zoom_config[value.name].get("light_level")
        if level:
            self.set_light_level(level)

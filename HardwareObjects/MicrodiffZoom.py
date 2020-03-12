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
MicrodiffZoom

Example xml file:
<device class="MicrodiffZoom">
  <username>zoom</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <value_channel_name>CoaxialCameraZoomValue</value_channel_name>
  <state_channel_name>ZoomState</state_channel_name>
  <values>[1, 2, 3, 4, 5, 6, 7]</values>
  <actuator_name>Zoom</actuator_name>
</device>
"""

import ast
import enum

from HardwareRepository.HardwareObjects.ExporterNState import ExporterNState

class MicrodiffZoom(ExporterNState):
    """MicrodiffZoom class"""

    def __init__(self, name):
        ExporterNState.__init__(self, name)
        self.predefined_positions = {}
        self._exporter = None
        self._limits = None
        self.position_channel = None
        self.motor_state = None

    def init(self):
        """Initialize the zoom"""
        ExporterNState.init(self)
        values = ast.literal_eval(self.getProperty("values"))
        self._nominal_limits = (values[0], values[-1])

        values = { ("LEVEL%s" % str(values.index(v) + 1)):v for v in values }
        values.update({"UNKNOWN": 0})

        self.VALUES = enum.Enum("MICRODIFF_ZOOM_ENUM", values)

    def get_limits(self):
        """Returns zoom low and high limits.
        Returns:
            (tuple): two int tuple (low limit, high limit).
        """
        return self._nominal_limits
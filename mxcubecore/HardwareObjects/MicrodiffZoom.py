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
</device>
"""


from enum import Enum
from HardwareRepository.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from HardwareRepository.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffZoom(ExporterNState):
    """MicrodiffZoom class"""
    def __init__(self, name):
        ExporterNState.__init__(self, name)

    def init(self):
        """Initialize the zoom"""
        ExporterNState.init(self)

        try:
            _low, _high = self._exporter.execute("getZoomRange")
            # inf is a problematic value
            if _low == float("-inf"):
                _low = 0

            if _high == float("inf"):
                _high = 10

            self.set_limits((_low, _high))
        except ValueError:
            self.set_limits((1, 10))

        self.initialise_values()

    def set_limits(self, limits=(None, None)):
        """Set the low and high limits.
        Args:
            limits (tuple): two element (low limit, high limit) tuple.
        """
        self._nominal_limits = limits

    def get_limits(self):
        """Returns zoom low and high limits.
        Returns:
            (tuple): two int tuple (low limit, high limit).
        """
        return self._nominal_limits

    def initialise_values(self):
        """Initialise the ValueEnum """
        low, high = self.get_limits()

        values = {
            "LEVEL%s" % str(v): v
            for v in range(low, high + 1)
        }
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )
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
MicrodiffZoom

Example xml file:
<object class="MicrodiffZoom">
  <username>zoom</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <value_channel_name>CoaxialCameraZoomValue</value_channel_name>
  <state_channel_name>ZoomState</state_channel_name>
  <!-- if levels do not corresponf to values -->
  <values>{"LEVEL1": 1, "LEVEL2": 2, "LEVEL3": 3, "LEVEL4": 4, "LEVEL5": 5, "LEV
EL6": 6}</values>
</object>
"""

from enum import Enum
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffZoom(ExporterNState):
    """MicrodiffZoom class"""

    def __init__(self, name):
        ExporterNState.__init__(self, name)

    def init(self):
        """Initialize the zoom"""
        ExporterNState.init(self)

        self.initialise_values()
        # check if we have values other that UKNOWN
        _len = len(self.VALUES) - 1
        if _len > 0:
            # we can only assume that the values are consecutive integers
            # so the limits correspond to the keys.
            self.set_limits((1, _len))
        else:
            # no values in the config file, initialise from the hardware.
            self.set_limits(self._get_range())
            self._initialise_values()

    def set_limits(self, limits=(None, None)):
        """Set the low and high limits.
        Args:
            limits (tuple): two integers tuple (low limit, high limit).
        """
        self._nominal_limits = limits

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emits signal limitsChanged.
        Args:
            limits (tuple): two integers tuple (low limit, high limit).
        """
        if not limits:
            limits = self.get_limits()

        # All values are not None nor NaN
        self._nominal_limits = limits
        self.emit("limitsChanged", (limits,))

    def _initialise_values(self):
        """Initialise the ValueEnum from the limits"""
        low, high = self.get_limits()

        values = {"LEVEL%s" % str(v): v for v in range(low, high + 1)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def _get_range(self):
        """Get the zoom range.
        Returns:
            (tuple): two integers tuple - min and max value.
        """
        try:
            _low, _high = self._exporter.execute("getZoomRange")
        except Exception:
            _low, _high = 1, 10

        # inf is a problematic value
        if _low == float("-inf"):
            _low = 1

        if _high == float("inf"):
            _high = 10

        return _low, _high

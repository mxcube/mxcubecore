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
"""
MicrodiffScintillator.

Example xml file:

.. code-block:: xml

  <object class="MicrodiffScintillator">
    <username>Scintilator</username>
    <exporter_address>xxx:9001</exporter_address>
    <value_channel_name>ScintillatorPosition</value_channel_name>
    <values>{"IN": "SCINTILLATOR", "OUT": "PARK"}</values>
    <state_channel_name>HardwareState</state_channel_name>
  </object>
"""

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDiffractometer import (
    DiffractometerPhase,
)
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffScintillator(ExporterNState):
    """Microdiff Scintillator class"""

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        # use phase when setting in
        if value == self.VALUES.IN:
            # use phase change instead of in
            HWR.beamline.diffractometer.set_phase(DiffractometerPhase.SEE_BEAM)
        else:
            super()._set_value(value)

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
Combine setting the back light IN with moving the beamstop out.
This is used to set the back light in/out faster, than using
the phase CENTRING - the beamstop motor moves only if needed.
Example xml configuration:

.. code-block:: xml
 <object class="MicrodiffLightInOut">
   <username>Back Light</username>
   <exporter_address>wid30bmd:9001</exporter_address>
   <value_channel_name>BackLightIsOn</value_channel_name>
   <values>{"IN": True, "OUT": False}</values>
   <state_channel_name>HardwareState</state_channel_name>
 </object>
"""
import logging
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState


__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffLightInOut(ExporterNState):
    """MicrodiffAperture class"""

    def _set_value(self, value):
        """Set device to value
        Args:
            value (str, int, float or enum): Value to be set.
        """
        # first move the beamstop in our out
        beamstop = HWR.beamline.diffractometer.beamstop
        if value == self.VALUES.IN:
            # set the beamstop off, if needed
            if beamstop.get_value() == beamstop.VALUES.IN:
                beamstop.set_value(beamstop.VALUES.OUT)
        super()._set_value(value)

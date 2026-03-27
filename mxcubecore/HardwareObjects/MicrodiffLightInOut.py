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
        if value == self.VALUES.IN and beamstop.get_value() == beamstop.VALUES.IN:
            beamstop.set_value(beamstop.VALUES.OUT)
        super()._set_value(value)

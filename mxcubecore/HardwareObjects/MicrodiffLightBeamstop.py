"""
Combine setting the back light IN with moving the beamstop out.
This is used to set the back light in/out faster, than using
the phase CENTRING - the beamstop motor moves only if needed.
It also makes sure the beamstop is in when in COLLECT phase.
Example xml configuration:

.. code-block:: xml
 <object class="MicrodiffLightBeamstop">
   <username>Back Light</username>
   <actuator_name>backlight</actuator_name>
   <exporter_address>xxx:9001</exporter_address>
   <value_channel_name>BackLightIsOn</value_channel_name>
   <values>{"IN": True, "OUT": False}</values>
   <state_channel_name>HardwareState</state_channel_name>
 or
   <username>Beamstop</username>
   <actuator_name>beamstop</actuator_name>
   <exporter_address>xxx:9001</exporter_address>
   <value_channel_name>BeamstopPosition</value_channel_name>
   <values>{"IN": "BEAM", "OUT": "OFF", "PARK": "PARK", "TRANSFER": "TRANSFER"}</values>
   <state_channel_name>HardwareState</state_channel_name>
 </object>
"""

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffLightBeamstop(ExporterNState):
    """MicrodiffLightBeamstop class"""

    def __init__(self, name):
        super().__init__(name)
        self.coupled_ctrl = None

    def _set_coupled_out(self):
        """Move the coupled device out."""
        if self.coupled_ctrl.get_value() == self.coupled_ctrl.VALUES.IN:
            # move the extra controlle out
            self.coupled_ctrl.set_value(self.coupled_ctrl.VALUES.OUT)

    def _set_coupled_in(self):
        """Move sure the coupled device in if needed. Usually needed when
        the phase is COLLECT and the beamstop is out.
        """
        diffr = HWR.beamline.diffractometer
        phase = diffr.current_phase
        if phase == diffr.get_phase_enum.COLLECT and "light" in self.actuator_name:
            self.coupled_ctrl.set_value(self.coupled_ctrl.VALUES.IN)

    def _set_value(self, value):
        """Set device to value.
        Args:
            value (str, int, float or enum): Value to be set.
        """
        self.coupled_ctrl = (
            HWR.beamline.diffractometer.beamstop
            if "light" in self.actuator_name
            else HWR.beamline.diffractometer.backlightswitch
        )

        # set the coupled device out first when the value is IN
        if value == self.VALUES.IN:
            self._set_coupled_out()

        super()._set_value(value)

        # set the coupled device in, if needed, when the value is OUT
        if value == self.VALUES.OUT:
            self._set_coupled_in()

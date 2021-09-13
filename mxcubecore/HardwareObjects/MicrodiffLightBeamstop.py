"""
Combine setting the back light IN with moving the beamstop out.
This is used to set the back light in/out faster, than using
the phase CENTRING - the beamstop motor moves only if needed.
Example xml file:
<device class="MicrodiffLightBeamstop">
  <username>Back Light</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <actuator_name>BackLightIsOn</actuator_name>
  <values>{"IN": True, "OUT": False}</values>
  <use_hwstate>True</use_hwstate>
  <object role="beamstop" href="/udiff_beamstop"/>
</device>
"""

from mxcubecore.HardwareObjects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffLightBeamstop(ExporterNState):
    """Control backlight, move the beamstop to safety position"""

    def __init__(self, name):
        super().__init__(name)
        self._beamstop_obj = None
        self._saved_beamstop_value = None

    def init(self):
        """Initialize the light and the beamstop object"""
        super().init()

        # get the beamstop object
        self._beamstop_obj = self.get_object_by_role("beamstop")

    def _set_value(self, value):
        """Set light to value. Move the beamstop, if needed.
        Args:
            value (enum): Value to be set.
        """
        if value == self.VALUES.IN:
            # move the beamstop backwords before setting the back light in
            if self._beamstop_obj:
                self.handle_beamstop(value)
            super()._set_value(value)
        else:
            super()._set_value(value)
            # move the beamstop if needed after getting the light out
            if self._beamstop_obj:
                self.handle_beamstop(value)

    def handle_beamstop(self, value):
        """ Move the beamstop as function of the value of the back light.
        Args:
            (enum): light value.
        """
        if value == self.VALUES.IN:
            self._saved_beamstop_value = self._beamstop_obj.get_value()
            # move the beamstop out to avoid collision with the back light
            self._beamstop_obj.set_value(self._beamstop_obj.VALUES.OUT, timeout=60)
        else:
            if self._saved_beamstop_value:
                self._beamstop_obj.set_value(self._saved_beamstop_value, timeout=60)
                self._saved_beamstop_value = None

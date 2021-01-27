"""
Combine setting the back light IN with moving the beamstop to a safety
position. This is used to set the back light in/out faster, than using
the phase CENTRING - the beamstop motor moves only if needed.
Example xml file:
<device class="MicrodiffLightBeamstop">
  <username>Back Light</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <actuator_name>BackLightIsOn</actuator_name>
  <values>{"IN": True, "OUT": False}</values>
  <use_hwstate>True</use_hwstate>
  <object role="beamstop" href="/udiff_bstopx"/>
  <safety_position>38</safety_position>
</device>
"""

from mxcubecore.hardware_objects.ExporterNState import ExporterNState

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MicrodiffLightBeamstop(ExporterNState):
    """Control backlight, move the beamstop to safety position"""

    def __init__(self, name):
        super(MicrodiffLightBeamstop, self).__init__(name)
        self.safety_position = None
        self._beamstop_obj = None
        self._saved_value = None

    def init(self):
        """Initialize the light and the beamstop object"""
        super(MicrodiffLightBeamstop, self).init()

        # for now the beamstop only moves in X directiron.
        self._beamstop_obj = self.get_object_by_role("beamstop")
        self.safety_position = float(self.get_property("safety_position", 38.0))

    def _set_value(self, value):
        """Set device to value. Move the beamstop, if needed.
        Args:
            value (enum): Value to be set.
        """
        # move the beamstop backwords before setting the back light in
        if self._beamstop_obj:
            self.handle_beamstop(value)
        else:
            super(MicrodiffLightBeamstop, self)._set_value(value)

    def handle_beamstop(self, value):
        """ Move the beamstop as function of the value of the back light.
        Args:
            (str): value name
        """
        if value.name == "IN":
            _pos = self._beamstop_obj.get_value()

            # only move if the beamstop is closer than the sefety_position
            if _pos < self.safety_position:
                self._saved_value = _pos
                self._beamstop_obj.set_value(self.safety_position, timeout=60)

            super(MicrodiffLightBeamstop, self)._set_value(value)

        elif value.name == "OUT":
            super(MicrodiffLightBeamstop, self)._set_value(value)

            if self._saved_value:
                self._beamstop_obj.set_value(self._saved_value, timeout=60)

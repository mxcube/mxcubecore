from enum import Enum

from mxcubecore.HardwareObjects.abstract.AbstractNState import (
    AbstractNState,
    BaseValueEnum,
)
from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator


class EPICSNState(EPICSActuator, AbstractNState):
    """
    This class manages devices that exist in a discrete number of states
    and provides an interface between those states (configured in the yaml
    files) and the EPICS PVs. It ensures that hardware states are treated as Enums.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSNState.EPICSNState
    epics:
      "MNC:B:PB03:PV_ACTIVATE_BACKLIGHT":
        channels:
          rbv:
            suffix: ':RBV'
            polling_period: 200
          val:
            suffix: ':SET'
    configuration:
      low_limit: 0
      high_limit: 1
      values: {'LEVEL0': 1, 'LEVEL1': 0}
    """

    def init(self):
        super().init()
        limits = self._nominal_limits
        EPICSActuator.set_limits(self, limits)
        self._initialise_values()
        current_value = self.get_value()
        self.update_value(current_value)

    def _set_value(self, value):
        if isinstance(value, Enum):
            value = value.value
        super()._set_value(value)

    def get_value(self):
        value = EPICSActuator.get_value(self)
        if not isinstance(value, Enum):
            value = self.value_to_enum(value)
        return value

    def _initialise_values(self):
        values = self.get_property("values")
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )

    def update_value(self, value=None) -> None:
        if value is None:
            return
        if not isinstance(value, Enum):
            value = self.value_to_enum(value)
        super().update_value(value)

    def hasnt_arrived(self, setpoint):
        if not isinstance(setpoint, Enum):
            setpoint = self.value_to_enum(setpoint)
        readback = self.get_value()
        if not readback:
            return False
        return setpoint != readback


class EPICSNStateInterval(EPICSNState):
    """
    This class is a workaround for devices that exist in a discrete number of states
    and do NOT have an on/off switch, but NEED to have a virtual on/off state in the
    GUI. Example: our frontlight device only allows for intensity setting (between 0
    and 20000), but does not have an on/off switch.

    This class implements the following logic: if the state of the device is higher
    than LEVEL1, it will be shown as on in the GUI. Otherwise, it will be shown as
    off in the GUI.

    Clicking on the icon when it is off will bring it to the LEVEL0 intensity value.
    Clicking on the icon when it is on will bring it to the LEVEL1 intensity value.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSNState.EPICSNStateInterval
    epics:
    "MNC:B:LUCIOLE01:LIGHT_CH2":
      channels:
        rbv:
          suffix: ''
          polling_period: 200
        val:
          suffix: ''
    configuration:
      low_limit: 0
      high_limit: 1
      values: {'LEVEL0': 15000, 'LEVEL1': 0}
    """

    def update_value(self, value=None) -> None:
        if value is None:
            return
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, int):
            return
        values_list = list(self.VALUES)
        if not (len(values_list) > 1):
            return
        enum_value = values_list[0] if value > values_list[1].value else values_list[1]
        super().update_value(enum_value)

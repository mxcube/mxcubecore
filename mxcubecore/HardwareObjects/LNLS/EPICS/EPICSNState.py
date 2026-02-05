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
        self.set_limits(limits)
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
        value = self.value_to_enum(value)
        super().update_value(value)

    def hasnt_arrived(self, setpoint):
        if not isinstance(setpoint, Enum):
            setpoint = self.value_to_enum(setpoint)
        readback = self.get_value()
        if not readback:
            return False
        return setpoint != readback

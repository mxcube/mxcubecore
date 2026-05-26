import time
from typing import Optional

import gevent
import numpy as np

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator
from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy


class EPICSActuator(AbstractActuator):
    ACTUATOR_VAL = "val"  # setpoint
    ACTUATOR_RBV = "rbv"  # readback

    def __init__(self, name):
        super().__init__(name)
        self.setpoint = None
        self._nominal_limits = (-1e4, 1e4)
        self.default_timeout = 180
        if not self.unit:
            self.unit = 10**-3

    def init(self):
        super().init()
        self.update_state(self.STATES.READY)
        self.connect(self.get_channel_object("rbv"), "update", self.update_value)

    def hasnt_arrived(self, setpoint):
        readback = self.get_value()
        if not readback:
            return False
        return not np.isclose(readback, setpoint, rtol=self.unit, atol=self.unit)

    def wait_ready(self, timeout: Optional[float] = None):
        self._ready_event.clear()
        is_set = self._ready_event.is_set()
        try:
            with gevent.Timeout(timeout, exception=TimeoutError):
                while not is_set:
                    is_set = self._ready_event.is_set()
                    if not self.hasnt_arrived(self.setpoint):
                        self._ready_event.set()
                    time.sleep(0.15)
        except TimeoutError:
            pvname = self.get_channel_object("").command.pv_name
            self.print_log(
                level="error",
                msg=f"{pvname} motion has timed out.",
            )
        self.update_state(self.STATES.READY)

    def get_value(self):
        return self.get_channel_value(self.ACTUATOR_RBV)

    def _set_value(self, value):
        self.setpoint = value
        self.update_state(self.STATES.BUSY)
        self.set_channel_value(self.ACTUATOR_VAL, value)

    def set_value(self, value, timeout: float = 0):
        if not timeout:
            timeout = self.default_timeout
        try:
            super().set_value(value, timeout)
        except ValueError:
            pvname = self.get_channel_object("rbv").command.pv_name
            msg = f"{pvname} value {value} is outside of actuator limits"
            msg += f": {self._nominal_limits}"
            self.print_log(
                level="error",
                msg=msg,
            )

    def abort(self):
        if self._wait_task is not None:
            self._wait_task.set()
        self.update_state(self.STATES.READY)


class EPICSActuatorBluesky(EPICSActuator):
    """
    This class alters the _set_value function of EPICSActuator for
    cases when the set is done via bluesky rather than directly by
    MXCuBE. The plan's name and parameter must be specified at the
    configuration file. Because wait_ready function works the same
    way as EPICSActuator, frontend functionality remains the same.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSActuator.EPICSActuatorBluesky
    epics:
    "MNC:A:DCM01:":
        channels:
        rbv:
            suffix: "GonRx_Energy_RBV"
            polling_period: 200
        val:
            suffix: "Energy_SP"
    configuration:
    tolerance: 0.01
    plan_name: "move_energy_and_phase"
    plan_parameter: "energy"
    default_limits: (5, 20)
    """

    def __init__(self, name):
        super().__init__(name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def init(self):
        super().init()
        self.plan_name = self.get_property("plan_name")
        self.plan_parameter = self.get_property("plan_parameter")

    def _set_value(self, value):
        self.setpoint = value
        self.update_state(self.STATES.BUSY)
        self._bluesky_api.execute_plan(
            plan_name=self.plan_name,
            kwargs={
                self.plan_parameter: value,
            },
        )


class LNLSEnergy(AbstractEnergy, EPICSActuatorBluesky):
    """
    This class is a specific workaround for LNLS energy
    component. It inherits from AbstractEnergy so that
    EnergyAdapter gets created, which is essential for
    the application to function properly.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.EPICS.EPICSActuator.EPICSActuatorBluesky
    epics:
    "MNC:A:DCM01:":
        channels:
        rbv:
            suffix: "GonRx_Energy_RBV"
            polling_period: 200
        val:
            suffix: "Energy_SP"
    configuration:
    tolerance: 0.01
    plan_name: "move_energy_and_phase"
    plan_parameter: "energy"
    default_lim
    """

    pass

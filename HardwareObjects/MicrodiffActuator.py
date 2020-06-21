"""
Use the exporter to set different MD2 actuators in/out.
If private_state not specified, True will be send to set in and False for out.
Example xml file:
<device class="MicrodiffActuator">
  <username>Scintilator</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <cmd_name>ScintillatorPosition</cmd_name>
  <private_state>{"PARK":"out", "SCINTILLATOR":"in"}</private_state>
  <use_hwstate>True</use_hwstate>
</device>
"""

import logging
import time
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)
from HardwareRepository.TaskUtils import task


class MicrodiffActuator(AbstractActuator):
    def __init__(self, name):
        AbstractActuator.__init__(self, name)
        self._hwstate_attr = None

    def init(self):
        self.cmd_name = self.get_property("cmd_name")
        self.username = self.get_property("username")
        self.cmd_attr = self.add_channel(
            {"type": "exporter", "name": "move"}, self.cmd_name
        )
        self.cmd_attr.connect_signal("update", self.value_changed)

        self.statecmd_name = self.get_property("statecmd_name")
        if self.statecmd_name is None:
            self.statecmd_name = self.cmd_name

        self.state_attr = self.add_channel(
            {"type": "exporter", "name": "state"}, self.statecmd_name
        )
        self.value_changed(self.state_attr.get_value())
        self.state_attr.connect_signal("update", self.value_changed)

        self.offset = self.get_property("offset")
        if self.offset > 0:
            self.states = {self.offset: "out", self.offset - 1: "in"}

        states = self.get_property("private_state")
        if states:
            import ast

            self.states = ast.literal_eval(states)
        try:
            tt = float(self.get_property("timeout"))
            self.timeout = tt
        except TypeError:
            pass

        if self.get_property("use_hwstate"):
            self.hwstate_attr = self.add_channel(
                {"type": "exporter", "name": "hwstate"}, "HardwareState"
            )

        self.swstate_attr = self.add_channel(
            {"type": "exporter", "name": "swstate"}, "State"
        )

        self._moves = dict((self.states[k], k) for k in self.states)

    def _ready(self):
        if self.hwstate_attr:
            if (
                self.hwstate_attr.get_value() == "Ready"
                and self.swstate_attr.get_value() == "Ready"
            ):
                return True
        else:
            if self.swstate_attr.get_value() == "Ready":
                return True
        return False

    def _wait_ready(self, timeout=None):
        timeout = timeout or self.timeout
        tt1 = time.time()
        while time.time() - tt1 < timeout:
            if self._ready():
                break
            else:
                time.sleep(0.5)

    def get_actuator_state(self, read=False):
        if read is True:
            value = self.state_attr.get_value()
            self.actuator_state = self.states.get(value, AbstractActuator.UNKNOWN)

        return self.actuator_state

    @task
    def actuator_in(self, wait=True, timeout=None):
        if self._ready():
            try:
                self.cmd_attr.setValue(self._moves["IN"])
                if wait:
                    timeout = timeout or self.timeout
                    self._wait_ready(timeout)
                self.value_changed(self.state_attr.get_value())
            except Exception as e:
                logging.getLogger("user_level_log").error(
                    "Cannot put %s in", self.username
                )
        else:
            logging.getLogger("user_level_log").error(
                "Microdiff is not ready, will not put %s in", self.username
            )

    @task
    def actuator_out(self, wait=True, timeout=None):
        if self._ready():
            try:
                self.cmd_attr.setValue(self._moves["OUT"])
                if wait:
                    timeout = timeout or self.timeout
                    self._wait_ready(timeout)
                self.value_changed(self.state_attr.get_value())
            except Exception as e:
                logging.getLogger("user_level_log").error(
                    "Cannot put %s out", self.username
                )
        else:
            logging.getLogger("user_level_log").error(
                "Microdiff is not ready, will not put %s out", self.username
            )

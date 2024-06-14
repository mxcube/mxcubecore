import logging
from mxcubecore.BaseHardwareObjects import HardwareObject
import time

"""
Use the exporter to set different MD2 actuators in/out.
If private_state not specified, True will be send to set in and False for out.
Example xml file:
<object class="MicrodiffInOut">
  <username>Scintilator</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <cmd_name>ScintillatorPosition</cmd_name>
  <private_state>{"PARK":"out", "SCINTILLATOR":"in"}</private_state>
  <use_hwstate>True</use_hwstate>
</object>
"""


class MicrodiffInOutMockup(HardwareObject):
    def __init__(self, name):
        Device.__init__(self, name)
        self.actuatorState = "unknown"
        self.username = "unknown"
        # default timeout - 3 sec
        self.timeout = 3
        self.hwstate_attr = None

    def init(self):
        self.cmd_name = self.get_property("cmd_name")
        self.username = self.get_property("username")

        self.states = {True: "in", False: "out"}
        self.state_attr = False
        self.offset = self.get_property("offset", 0)
        if self.offset > 0:
            self.states = {self.offset: "out", self.offset - 1: "in"}

        states = self.get_property("private_state")
        if states:
            import ast

            self.states = ast.literal_eval(states)
        try:
            tt = float(self.get_property("timeout"))
            self.timeout = tt
        except Exception:
            pass

        self.moves = dict((self.states[k], k) for k in self.states)

    def connect_notify(self, signal):
        if signal == "actuatorStateChanged":
            self.value_changed(self.state_attr)

    def value_changed(self, value):
        self.actuatorState = self.states.get(value, "unknown")
        self.emit("actuatorStateChanged", (self.actuatorState,))

    def _ready(self):
        return True

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
            value = self.state_attr
            self.actuatorState = self.states.get(value, "unknown")
            self.connect_notify("actuatorStateChanged")
        else:
            if self.actuatorState == "unknown":
                self.connect_notify("actuatorStateChanged")
        return self.actuatorState

    def actuatorIn(self, wait=True, timeout=None):
        if self._ready():
            try:
                self.state_attr = self.moves["in"]
                if wait:
                    timeout = timeout or self.timeout
                    self._wait_ready(timeout)
                self.value_changed(self.state_attr)
            except Exception:
                logging.getLogger("user_level_log").error(
                    "Cannot put %s in", self.username
                )
        else:
            logging.getLogger("user_level_log").error(
                "Microdiff is not ready, will not put %s in", self.username
            )

    def actuatorOut(self, wait=True, timeout=None):
        if self._ready():
            try:
                self.state_attr = self.moves["out"]
                if wait:
                    timeout = timeout or self.timeout
                    self._wait_ready(timeout)
                self.value_changed(self.state_attr)
            except Exception:
                logging.getLogger("user_level_log").error(
                    "Cannot put %s out", self.username
                )
        else:
            logging.getLogger("user_level_log").error(
                "Microdiff is not ready, will not put %s out", self.username
            )

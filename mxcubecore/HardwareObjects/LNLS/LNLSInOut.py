import logging
import time

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.HardwareObjects.LNLS.EPICSActuator import EPICSActuator

"""
Use the exporter to set different MD2 actuators in/out.
If private_state not specified, True will be send to set in and False for out.
Example xml file:
<device class="MicrodiffInOut">
  <username>Scintilator</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <cmd_name>ScintillatorPosition</cmd_name>
  <private_state>{"PARK":"out", "SCINTILLATOR":"in"}</private_state>
  <use_hwstate>True</use_hwstate>
</device>
"""


class LNLSInOut(EPICSActuator, Device):
    def __init__(self, name):
        EPICSActuator.__init__(self, name)
        Device.__init__(self, name)
        self.actuatorState = "unknown"
        self.username = "unknown"
        # default timeout - 3 sec
        self.timeout = 3
        self.hwstate_attr = None

    def init(self):
        self.cmdname = self.getProperty("cmd_name")
        self.username = self.getProperty("username")

        self.states = {True: "in", False: "out"}

        # Initialize widget state
        current_value = self.get_value()
        value = bool(current_value)
        self.state_attr = value
        self.actuatorState = self.states.get(value, "unknown")
        self.emit("actuatorStateChanged", (self.actuatorState,))

        self.offset = self.getProperty("offset", 0)
        if self.offset > 0:
            self.states = {self.offset: "out", self.offset - 1: "in"}

        states = self.getProperty("private_state")
        if states:
            import ast

            self.states = ast.literal_eval(states)
        try:
            tt = float(self.getProperty("timeout"))
            self.timeout = tt
        except BaseException:
            pass

        self.moves = dict((self.states[k], k) for k in self.states)

    def connectNotify(self, signal):
        if signal == "actuatorStateChanged":
            self.valueChanged(self.state_attr)

    def valueChanged(self, value):
        super(LNLSInOut, self).set_value(value)
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
            self.connectNotify("actuatorStateChanged")
        else:
            if self.actuatorState == "unknown":
                self.connectNotify("actuatorStateChanged")
        return self.actuatorState

    def actuatorIn(self, wait=True, timeout=None):
        if self._ready():
            try:
                self.state_attr = self.moves["in"]
                if wait:
                    timeout = timeout or self.timeout
                    self._wait_ready(timeout)
                self.valueChanged(self.state_attr)
            except BaseException:
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
                self.valueChanged(self.state_attr)
            except BaseException:
                logging.getLogger("user_level_log").error(
                    "Cannot put %s out", self.username
                )
        else:
            logging.getLogger("user_level_log").error(
                "Microdiff is not ready, will not put %s out", self.username
            )

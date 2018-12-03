"""
Actuators have two positions - 'IN' and 'OUT'.
"""

import logging
from warnings import warn
from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.TaskUtils import task


class AbstractActuator(Device):

    (UNKNOWN, IN, OUT, MOVING) = ("unknown", "in", "out", "moving")

    def __init__(self, name):
        Device.__init__(self, name)
        self.actuator_state = AbstractActuator.UNKNOWN
        self.username = "unknown"
        # default timeout - 3 sec
        self._timeout = 3
        self.states = {True: "IN", False: "OUT"}

    def connectNotify(self, signal):
        if signal == "actuatorStateChanged":
            self.value_changed(self.get_actuator_state(read=True))

    def value_changed(self, value):
        self.actuator_state = self.states.get(value, AbstractActuator.UNKNOWN)
        self.emit("actuatorStateChanged", (self.actuator_state.lower(),))

    def get_actuator_state(self, read=False):
        """Return the state value
           Args:
             read (bool): read the hardware if True
           Returns:
             (string): the state
        """
        logging.getLogger().info("%s state: %r" % (self.username, self.actuator_state))
        return self.actuator_state

    @task
    def actuator_in(self, wait=True, timeout=3):
        """Set the actuator 'in'. Update the status
           Keyword Args:
             wait (bool): wait for the movement to finish
             timeout (float): movement expires after timeout [s]
        """
        self.value_changed(self.actuator_state)

    @task
    def actuator_out(self, wait=True, timeout=3):
        """Set the actuator 'out'. Update the status
           Keyword Args:
             wait (bool): wait for the movement to finish
             timeout (float): movement expires after timeout [s]
        """
        self.value_changed(self.actuator_state)

    @task
    def actuator_toggle(self, wait=True, timeout=3):
        """Toggele the actuator.
           Keyword Args:
             wait (bool): wait for the movement to finish
             timeout (float): movement expires after timeout [s]
        """
        if self.actuator_state == AbstractActuator.IN:
            self.actuator_out(wait, timeout)
        elif self.actuator_state == AbstractActuator.OUT:
            self.actuator_in(wait, timeout)

    def getActuatorState(self, read=False):
        warn(
            "getActuatorState method is deprecated, use get_actuator_state",
            DeprecationWarning,
        )
        return self.get_actuator_state(read)

    def actuatorIn(self, wait=True, timeout=3):
        warn("actuatorIn method is deprecated, use actuator_in", DeprecationWarning)
        self.actuator_in(wait, timeout)

    def actuatorOut(self, wait=True, timeout=3):
        warn("actuatorOut method is deprecated, use actuator_out", DeprecationWarning)
        self.actuator_out(wait, timeout)

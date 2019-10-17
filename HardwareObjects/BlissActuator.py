"""
Use bliss to set different actuators in/out.
If private_state not specified, True will be send to set in and False for out.
Example xml file:
<device class="BlissActuator">
  <username>Detector Cover</username>
  <object href="/bliss" role="controller"/>
</device>
"""
import logging

from HardwareRepository.HardwareObjects.abstract.AbstractTwoState import (
    AbstractTwoState
)
from HardwareRepository.TaskUtils import task


class BlissActuator(AbstractTwoState):
    def __init__(self, name):
        AbstractTwoState.__init__(self, name)

    def init(self):
        self.username = self.getProperty("username")
        name = self.getProperty("name")
        self._actuator = getattr(self.getObjectByRole("controller"), name)
        self.states = {"IN": "IN", "OUT": "OUT"}
        self.value_changed(self._actuator.state())

    def get_actuator_state(self, read=False):
        if read is True:
            value = self._actuator.state()
            self.actuator_state = self.states.get(value, AbstractTwoState.UNKNOWN)
        else:
            if self.actuator_state == AbstractTwoState.UNKNOWN:
                self.connectNotify("actuatorStateChanged")

        logging.getLogger().debug("%s state: %s" % (self.username, self.actuator_state))
        return self.actuator_state

    @task
    def actuator_in(self, wait=True, timeout=None):
        self._actuator.set_in()
        self.value_changed(self._actuator.state())

    def actuator_out(self, wait=True, timeout=3):
        self._actuator.set_out()
        self.value_changed(self._actuator.state())

    # Compatability with camelcase API
    getActuatorState = get_actuator_state
    actuatorIn = actuator_in
    actuatorOut = actuator_out

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
from warnings import warn

from mx3core.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)
from mx3core.TaskUtils import task


class BlissActuator(AbstractActuator):
    def __init__(self, name):
        warn(
            "BlissActuator class is deprecated. Use BlissNState instead",
            DeprecationWarning,
        )
        AbstractActuator.__init__(self, name)

    def init(self):
        self.username = self.get_property("username")
        name = self.get_property("name")
        self._actuator = getattr(self.get_object_by_role("controller"), name)
        self.states = {"IN": "IN", "OUT": "OUT"}
        self.value_changed(self._actuator.state())

    def get_actuator_state(self, read=False):
        if read is True:
            value = self._actuator.state()
            self.actuator_state = self.states.get(value, AbstractActuator.UNKNOWN)
        else:
            if self.actuator_state == AbstractActuator.UNKNOWN:
                self.connect_notify("actuatorStateChanged")

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
    actuatorIn = actuator_in
    actuatorOut = actuator_out

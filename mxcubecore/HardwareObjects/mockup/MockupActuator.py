"""
Actuator mockup
If private_state not specified, True will be send to set in and False for out.
Example xml file:
<device class="MockupActuator">
  <username>Detector Cover</username>
  <name>detcover</name>
  <private_state>{'OUT': 'PARK',  'IN': 'SCINTILLATOR'}</private_state>
</device>
"""
import logging
from HardwareRepository.TaskUtils import task

import logging

from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator
)

class MockupActuator(AbstractActuator):
    def __init__(self, name):
        AbstractActuator.__init__(self, name)

    def init(self):
        self.username = self.getProperty("username")
        self.name = self.getProperty("name")
        states = self.getProperty("private_state")
        if states:
            import ast

            self.states = ast.literal_eval(states)
        self._moves = dict((self.states[k], k) for k in self.states)
        self.actuator_state = self._moves["OUT"]

    def get_actuator_state(self, read=False):
        logging.getLogger().info("%s state: %r" % (self.username, self.actuator_state))
        return self.actuator_state

    @task
    def actuator_in(self, wait=True, timeout=3):
        logging.getLogger().info(
            "%s moving to %r" % (self.username, (self._moves["IN"]))
        )
        self.value_changed(self._moves["IN"])

    @task
    def actuator_out(self, wait=True, timeout=3):
        logging.getLogger().info(
            "%s moving to %r" % (self.username, (self._moves["OUT"]))
        )
        self.value_changed(self._moves["OUT"])

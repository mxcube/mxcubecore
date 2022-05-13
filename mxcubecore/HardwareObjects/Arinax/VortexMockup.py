# -*- coding: utf-8 -*-
"""

XML Configuration Example:

* With state attribute and open/close commands

<device class = "Arinax.SafetyShutter">
  <username>FrontEnd</username>
  <command type="epics" name="Open">Open</command>
  <command type="epics" name="Close">Close</command>
  <channel type="epics" name="State">State</channel>
</device>

* With read/write attribute :

<device class = "Arinax.SafetyShutter">
  <username>Safety Shutter</username>
  <channel type="epics" name="safetyShutterState">Epics PV</channel>
</device>

"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import HardwareObject

import logging


class VortexMockup(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.state = "UNKNOWN"

    def init(self):

        self.state = "READY"

    def set_preset(self, integration_time):
        pass

    def set_roi(self, roi_start, roi_end):
        pass

    def get_roi_count(self):
        pass

    def start(self):
        self.state = "RUNNING"

    def wait(self):
        self.state = "READY"

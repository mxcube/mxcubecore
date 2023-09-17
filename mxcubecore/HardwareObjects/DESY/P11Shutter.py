#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""P11Shutter"""

import time
import gevent
import urllib
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from enum import Enum, unique


__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"


class P11Shutter(AbstractShutter):
    """
    P11 Shutter define interface to Tango shutters at DESY P11
    """

    default_timeout = 6

    @unique
    class BaseValueEnum(Enum):
     """Defines only the compulsory values."""
     OPEN = "OPEN"
     CLOSED = "CLOSED"
     MOVING = "MOVING"
     UNKNOWN = "UNKNOWN"
    
    VALUES=BaseValueEnum

    def __init__(self, name):

        super(AbstractShutter, self).__init__(name)

        self.simulation = False
        self.simulated_opened = True
        self.simulated_moving = False

        self.url_open = None
        self.url_closee = None
        self.cmd_started = 0

        self.chan_state = None

    def init(self):
        """Initilise the predefined values"""

        # if simulation is set - open and close will be mere software flags

        self.simulation = self.get_property("simulation")

        if not self.simulation:
            url_base = self.get_property("base_url")
            dev_open = self.get_property("device_open")
            dev_close = self.get_property("device_close")
            self.url_open = "{}&deviceName={}".format(url_base, dev_open)
            self.url_close = "{}&deviceName={}".format(url_base, dev_close)

            self.chan_state = self.get_channel_object("chanState")

            if self.chan_state is not None:
                self.chan_state.connect_signal("update", self.update_shutter_state)

            self.update_shutter_state()
        else:
            self.simulated_update()

        super(AbstractShutter, self).init()

    def get_value(self):
        if self.simulation:
            return self.simulated_update()

        return self.update_shutter_state()

    def _set_value(self, value):
        if value == self.VALUES.OPEN:
            open_it = 1
        elif value == self.VALUES.CLOSED:
            open_it = 0
        else:
            self.log.debug(" ###  setting wrong value for shutter %s" % str(value))
            return

        if self.simulation:
            self.simulated_opened = open_it
            self.simulated_moving = True
            gevent.spawn(self.simul_do)
        else:
            if open_it:
                self.do_open()
            else:
                self.do_close()
            self.cmd_started = time.time()

    def do_open(self, timeout=3):
        result = urllib.request.urlopen(self.url_open, None, timeout).readlines()

    def do_close(self, timeout=3):
        result = urllib.request.urlopen(self.url_close, None, timeout).readlines()

    def simul_do(self):
        gevent.sleep(1)
        self.simulated_moving = False
        self.log.debug("### updating simulated shutter")
        self.simulated_update()

    def update_shutter_state(self, state=None):
        """Updates shutter state 

        :return: shutter state as str
        """
        if state is None:
            state = self.chan_state.get_value()

        if state[0] == 3:
            value = self.VALUES.OPEN
        else:
            value = self.VALUES.CLOSED

        # else:
        #     if time.time() - self.cmd_started > self.cmd_timeout:
        #        value = self.VALUES.UNKNOWN
        #     else:
        #        value = self.VALUES.MOVING

        self.update_value(value)

        return value

    def simulated_update(self):
        if self.simulated_moving:
            value = self.VALUES.MOVING
        elif self.simulated_opened:
            value = self.VALUES.OPEN
        else:
            value = self.VALUES.CLOSED

        self.update_value(value)

        return value


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
import logging
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState


__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"


class P11Shutter(AbstractShutter):
    """
    P11 Shutter define interface to Tango shutters at DESY P11
    """

    default_timeout = 6

    def __init__(self,name):

        super(AbstractShutter,self).__init__(name)

        self.simulation = False
        self.simulated_opened = True
        self.simulated_moving = False

        self.cmd_open_close = None
        self.cmd_started = 0

        self.chan_state_open = None
        self.chan_state_close = None
        

    def init(self):
        """Initilise the predefined values"""

        # if simulation is set - open and close will be mere software flags

        self.cmd_timeout = self.get_property("command_timeout", self.default_timeout)
        self.simulation = self.get_property("simulation")

        if not self.simulation:
            self.cmd_open_close = self.get_command_object("cmdOpenClose")

            self.chan_state_open = self.get_channel_object("chanStateOpen")
            self.chan_state_closed = self.get_channel_object("chanStateClosed")


            if self.chan_state_open is not None:
                self.chan_state_open.connect_signal("update", self.state_open_changed)
            if self.chan_state_open is not None:
                self.chan_state_closed.connect_signal("update", self.state_closed_changed)

            self.state_open_changed(self.chan_state_open.get_value())
        else:
            self.simulated_update()

        super(AbstractShutter,self).init()

    def get_value(self):
        if self.simulation:
            return self.simulated_update()

        is_opened = self.chan_state_open.get_value()
        is_closed = self.chan_state_closed.get_value()
        return self.update_shutter_state(opened=is_opened,closed=is_closed)
       
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
            self.cmd_open_close(open_it)
            self.cmd_started = time.time()

    def simul_do(self):
        gevent.sleep(1)
        self.simulated_moving = False
        self.log.debug("### updating simulated shutter")
        self.simulated_update()

    def state_open_changed(self, value):
        """Updates shutter state when shutter open value changes

        :param state: shutter open state
        :type state: str
        :return: None
        """
        self.update_shutter_state(opened=value)

    def state_closed_changed(self, value):
        """Updates shutter state when shutter close value changes

        :param state: shutter close state
        :type state: str
        :return: None
        """
        self.update_shutter_state(closed=value)

    def update_shutter_state(self, opened=None, closed=None):
        """Updates shutter state 

        :return: shutter state as str
        """
        if opened == 0:
             value = self.VALUES.OPEN
        elif closed == 0:
             value = self.VALUES.CLOSED
        else:
            if time.time() - self.cmd_started > self.cmd_timeout:
                value = self.VALUES.UNKNOWN
            else:
                value = self.VALUES.MOVING

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

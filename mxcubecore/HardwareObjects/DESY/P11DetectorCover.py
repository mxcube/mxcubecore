#
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

"""P11DetectorCover"""

import logging
import time
import gevent

from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState


__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"

class P11DetectorCover(AbstractShutter):
    """
    P11DetectorCover define interface to Tango Detector Cover at DESY P11

    Similar to P11 Shutter tango - but differs
    """
    default_timeout = 4
    move_time_min = 1

    def __init__(self,name):

        super(AbstractShutter,self).__init__(name)

        self.simulation = False
        self.simulated_opened = False
        self.simulated_moving = False

        self.cmd_open = None
        self.cmd_close = None
        self.cmd_started = 0

        self.chan_state_open = None
        self.chan_state_close = None

        self.cover_is_open = False
        self.cover_is_closed = False

    def init(self):
        """Initilise the predefined values"""

        self.simulation = self.get_property("simulation")
        self.cmd_timeout = self.get_property("command_timeout", self.default_timeout)

        if not self.simulation:
            self.cmd_open = self.get_command_object("cmdOpen")
            self.cmd_close = self.get_command_object("cmdClose")
    
            self.chan_state_open = self.get_channel_object("chanStateOpen")
            self.chan_state_closed = self.get_channel_object("chanStateClosed")

            if self.chan_state_open is not None:
                self.chan_state_open.connect_signal("update", self.state_open_changed)
            else:
                self.log.error("Cannot get channel for shutter %s" % self.username)

            if self.chan_state_closed is not None:
                self.chan_state_closed.connect_signal("update", self.state_closed_changed)
            else:
                self.log.error("Cannot get channel for shutter %s" % self.username)

            self.state_open_changed(self.chan_state_open.get_value())
        else:
            self.simulated_update()

        super(AbstractShutter,self).init()

    def get_value(self):
        if self.simulation:
            return self.simulated_update()

        if self._nominal_value == self.VALUES.MOVING:
            if (time.time() - self.cmd_started) < self.move_time_min:
                return self.VALUES.MOVING

        self.cover_is_open = self.chan_state_open.get_value()
        self.cover_is_closed = self.chan_state_closed.get_value()
        return self.update_cover_state()

    def _set_value(self, value):

        if self.simulation:
            if value == self.VALUES.OPEN:
                self.simulated_opened = 1
            else:
                self.simulated_opened = 0
            self.simulated_moving = True
            gevent.spawn(self.simul_do)
            return

        current_value = self.get_value()

        if current_value == self.VALUES.MOVING:
            self.log.error("Cannot move while moving")
            return 

        if value != current_value:
            if value == self.VALUES.OPEN:
                self.cmd_open()
            elif value == self.VALUES.CLOSED:
                self.cmd_close()

            self.cmd_started = time.time()
            self.update_value(self.VALUES.MOVING)

    def simul_do(self):
        gevent.sleep(3)
        self.simulated_moving = False
        self.simulated_update()

    def is_moving(self):
        return self.get_value() == self.VALUES.MOVING

    def state_open_changed(self, value):
        """Updates cover state when cover open value changes

        :param state: cover open state
        :type state: str
        :return: None
        """
        self.cover_is_open = value
        self.update_cover_state()

    def state_closed_changed(self, value):
        """Updates cover state when cover close value changes

        :param state: cover close state
        :type state: str
        :return: None
        """
        self.cover_is_closed = value
        self.update_cover_state()

    def update_cover_state(self):
        """Updates cover state 

        :return: cover state as str
        """
        if self.cover_is_open:
            value = self.VALUES.OPEN
        elif self.cover_is_closed:
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

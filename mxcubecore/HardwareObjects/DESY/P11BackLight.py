# encoding: utf-8
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

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

from enum import (
    Enum,
    unique,
)

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractNState

__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"

import time
from enum import (
    Enum,
    unique,
)

from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter


@unique
class BackLightValues(Enum):
    IN = "In"
    OUT = "Out"
    MOVING = "Moving"
    UNKNOWN = "UNKNOWN"


class P11BackLight(AbstractNState):
    """
    P11 BakcLight define interface to Tango backlight at DESY P11
    """

    VALUES = BackLightValues

    default_open_time = 8
    default_close_time = 3

    def __init__(self, name):

        super().__init__(name)

        self.cmd_open_close = None
        self.cmd_started = 0

        self.chan_state_open = None
        self.chan_state_close = None

    def init(self):
        """Initilise the predefined values"""

        self.chan_value = self.get_channel_object("value")
        self.open_time = self.get_property("open_time", self.default_open_time)
        self.close_time = self.get_property("close_time", self.default_close_time)

        if self.chan_value is not None:
            self.chan_value.connect_signal("update", self.update_light_state)

        self.update_light_state(self.chan_value.get_value())
        super().init()

    def get_value(self):
        return self.update_light_state()

    def is_moving(self):
        return self.get_value() == self.VALUES.MOVING

    def is_in(self):
        return self.get_value() == self.VALUES.IN

    def is_out(self):
        return self.get_value() == self.VALUES.OUT

    def set_in(self):
        self.set_value(self.VALUES.IN)

    def set_out(self):
        self.set_value(self.VALUES.OUT)

    def _set_value(self, value):
        current_value = self.chan_value.get_value()

        if value == self.VALUES.IN:
            new_value = 1
        elif value == self.VALUES.OUT:
            new_value = 0

        if current_value != new_value:
            self.chan_value.set_value(new_value)
            self.cmd_started = time.time()

    def update_light_state(self, value=None):
        """Updates light state 

        :return: light state as str
        """
        if value is None:
            value = self.chan_value.get_value()

        elapsed = time.time() - self.cmd_started

        if value == 1:
            if elapsed < self.open_time:
                light_value = self.VALUES.MOVING
            else:
                light_value = self.VALUES.IN
        elif value == 0:
            if elapsed < self.close_time:
                light_value = self.VALUES.MOVING
            else:
                light_value = self.VALUES.OUT
        else:
            light_value = self.VALUES.UNKNOWN

        self.update_value(light_value)

        return light_value

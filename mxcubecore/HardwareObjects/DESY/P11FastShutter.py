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

from enum import Enum

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractNState

__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "General"

from enum import Enum

from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter


class P11FastShutter(AbstractNState):
    """
    P11 BakcLight define interface to Tango backlight at DESY P11
    """

    default_open_time = 8
    default_close_time = 3

    def __init__(self, name):
        super().__init__(name)
        self.chan_value = None

    def init(self):
        """Initilise the predefined values"""

        self._initialise_values()
        self.chan_value = self.get_channel_object("value")

        if self.chan_value is not None:
            self.chan_value.connect_signal("update", self.update_fast_shutter)

        self.update_fast_shutter(self.chan_value.get_value())
        super().init()

    def _initialise_values(self):
        """Add additional, known in advance states to VALUES"""
        values_dict = {item.name: item.value for item in self.VALUES}
        values_dict.update({"OPEN": "Open", "CLOSED": "Closed"})
        self.VALUES = Enum("ValueEnum", values_dict)

    def get_value(self):
        return self.update_fast_shutter()

    @property
    def is_open(self):
        return self.get_value() == self.VALUES.OPEN

    @property
    def is_closed(self):
        return self.get_value() == self.VALUES.CLOSED

    def open(self):
        self.set_value(self.VALUES.OPEN)

    def close(self):
        self.set_value(self.VALUES.CLOSED)

    def _set_value(self, value):
        current_value = self.chan_value.get_value()

        if value == self.VALUES.OPEN:
            new_value = 1
        elif value == self.VALUES.CLOSED:
            new_value = 0

        if current_value != new_value:
            self.chan_value.set_value(new_value)

    def update_fast_shutter(self, value=None):
        """Updates shutter state

        :return: shutter state as str
        """
        if value is None:
            value = self.chan_value.get_value()

        if value:
            shutter_value = self.VALUES.OPEN
        else:
            shutter_value = self.VALUES.CLOSED

        self.update_value(shutter_value)

        return shutter_value

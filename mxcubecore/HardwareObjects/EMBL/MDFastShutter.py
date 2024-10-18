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


from enum import (
    Enum,
    unique,
)

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


@unique
class ShutterValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "Open"
    CLOSED = "Closed"
    UNKNOWN = "Unknown"
    DISABLED = "Disabled"


class MDFastShutter(AbstractShutter):
    """
    MD Fast shutter
    """

    VALUES = ShutterValueEnum

    def __init__(self, name):
        """
        init
        :param name:
        """
        super(MDFastShutter, self).__init__(name)

        self._nominal_limits = None

        self.chan_shutter_is_open = None
        self.chan_current_phase = None

        self.shutter_is_open = None
        self.current_phase = None

    def init(self):
        super(MDFastShutter, self).init()

        self.chan_shutter_is_open = self.get_channel_object("chanShutterIsOpen")
        if self.chan_shutter_is_open:
            self.chan_shutter_is_open.connect_signal("update", self.shutter_is_open_changed)

        self.chan_current_phase = self.get_channel_object("chanCurrentPhase")
        if self.chan_current_phase is not None:
            self.current_phase = self.chan_current_phase.get_value()
            self.connect(self.chan_current_phase, "update", self.current_phase_changed)

    def shutter_is_open_changed(self, value):
        """
        Shutter state changed event
        :param value:
        :return:
        """
        self.shutter_is_open = value
        #We allow to control the fast shutter just in the beam location phase
        if self.current_phase == "BeamLocation":
            if value:
                value = self.VALUES.OPEN
            else:
                value = self.VALUES.CLOSED
        else:
            value = self.VALUES.DISABLED
        print("is open changed ", value, self.shutter_is_open)
        self.update_value(value)

    def get_value(self):
        return self._nominal_value

    def current_phase_changed(self, value):
        """
        Phase changed
        :param value: str
        :return:
        """
        self.current_phase = value
        self.shutter_is_open_changed(self.chan_shutter_is_open.get_value())

    def _set_value(self, value):
        if value == self.VALUES.OPEN:
            self.chan_shutter_is_open.set_value(True)
        elif value == self.VALUES.CLOSED:
            self.chan_shutter_is_open.set_value(False)

    def open_delete(self, wait=True):
        """
        Opens the shutter
        :param wait:
        :return:
        """
        self.chan_shutter_is_open.set_value(True)
        with gevent.Timeout(10, Exception("Timeout waiting for fast shutter open")):
            while not self.shutter_is_open:
                gevent.sleep(0.1)

    def close_delete(self, wait=True):
        """
        Closes shutter
        :param wait: boolean
        :return:
        """
        self.chan_shutter_is_open.set_value(False)
        with gevent.Timeout(10, Exception("Timeout waiting for fast shutter close")):
            while self.shutter_is_open:
                gevent.sleep(0.1)

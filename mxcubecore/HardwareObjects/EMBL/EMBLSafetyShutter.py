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

"""EMBLSafetyShutter"""

import logging
from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"

@unique
class ShutterValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "Open"
    CLOSED = "Closed"
    UNKNOWN = "Unknown"
    NOPERM = "No permission"
    DISABLED = "Disabled"


class EMBLSafetyShutter(AbstractShutter):
    """
    EMBLSafetyShutter defines interface to DESY ics
    """

    VALUES = ShutterValueEnum

    def __init__(self, name):
        super(EMBLSafetyShutter, self).__init__(name)

        self._nominal_limits = None

        self.use_shutter = None
        self.data_collection_state = None
        self.shutter_can_open = None
        self.shutter_is_open = None
        self.shutter_is_closed = None
        # GB 20190304: per misteriously disappearing first update of
        # shutter_state_closed:
        self.shutter_can_open = None
        self.ics_enabled = None

        self.chan_collection_state = None
        self.chan_state_open = None
        self.chan_state_closed = None
        self.chan_state_open_permission = None
        self.chan_ics_error = None
        self.chan_error = None
        self.chan_cmd_close_error = None
        self.chan_cmd_open_error = None
        self.cmd_open = None
        self.cmd_close = None


    def init(self):
        super(EMBLSafetyShutter, self).init()

        self.chan_collection_state = self.get_channel_object("chanCollectStatus")
        if self.chan_collection_state:
            self.chan_collection_state.connect_signal(
                "update", self.data_collection_state_changed
            )

        self.chan_state_closed = self.get_channel_object("chanStateClosed")
        self.chan_state_closed.connect_signal("update", self.state_closed_changed)
        self.chan_state_open = self.get_channel_object("chanStateOpen")
        self.chan_state_open.connect_signal("update", self.state_open_changed)

        self.chan_state_open_permission = self.get_channel_object(
            "chanStateOpenPermission"
        )
        self.chan_state_open_permission.connect_signal(
            "update", self.state_open_permission_changed
        )
        self.state_open_permission_changed(self.chan_state_open_permission.get_value())

        self.chan_ics_error = self.get_channel_object("chanIcsError")
        self.chan_ics_error.connect_signal("update", self.ics_error_msg_changed)
        self.ics_error_msg_changed(self.chan_ics_error.get_value())

        self.chan_cmd_close_error = self.get_channel_object("chanCmdCloseError")
        if self.chan_cmd_close_error is not None:
            self.chan_cmd_close_error.connect_signal(
                "update", self.cmd_error_msg_changed
            )

        self.chan_cmd_open_error = self.get_channel_object("chanCmdOpenError")
        if self.chan_cmd_open_error is not None:
            self.chan_cmd_open_error.connect_signal(
                "update", self.cmd_error_msg_changed
            )

        self.cmd_open = self.get_command_object("cmdOpen")
        self.cmd_close = self.get_command_object("cmdClose")

        self.use_shutter = self.get_property("useShutter", True)

        self.state_open_changed(self.chan_state_open.get_value())

    def data_collection_state_changed(self, state):
        """Updates shutter state when data collection state changes

        :param state: data collection state
        :type state: str
        :return: None
        """
        self.data_collection_state = state
        self.update_shutter_state()

    def state_open_changed(self, state):
        """Updates shutter state when shutter open value changes

        :param state: shutter open state
        :type state: str
        :return: None
        """

        self.shutter_is_open = state
        self.update_shutter_state()

    def state_closed_changed(self, state):
        """Updates shutter state when shutter close value changes

        :param state: shutter close state
        :type state: str
        :return: None
        """
        self.shutter_is_closed = state
        self.update_shutter_state()

    def state_open_permission_changed(self, state):
        """Updates shutter state when open permission changes

        :param state: permission state
        :type state: str
        :return: None
        """
        self.shutter_can_open = state
        self.update_shutter_state()

    def cmd_error_msg_changed(self, error_msg):
        """Method called when opening of the shutter fails

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0:
            logging.getLogger("GUI").error("Safety shutter: Error %s" % error_msg)

    def ics_error_msg_changed(self, error_msg):
        """Updates ICS error message

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0:
            logging.getLogger("GUI").error("DESY ICS Connection: Error %s" % error_msg)
            self.ics_enabled = False
        else:
            self.ics_enabled = True
        self.update_shutter_state()

    def update_shutter_state(self):
        """Updates shutter state

        :return: shutter state as str
        """
        msg = ""

        if self.data_collection_state == "collecting":
            value = self.VALUES.DISABLED
        elif self.shutter_is_open:
            value = self.VALUES.OPEN
        elif self.shutter_is_closed:
            value = self.VALUES.CLOSED
        elif not self.shutter_can_open:
            value = self.VALUES.DISABLED
        else:
            value = self.VALUES.UNKNOWN

        if not self.shutter_is_open and not self.shutter_can_open:
            value = self.VALUES.NOPERM
            msg = "No permission"

        if not self.ics_enabled:
            value = self.VALUES.DISABLED
            msg = "Ics broke"

        if not self.use_shutter:
            value = self.VALUES.DISABLED

        self.update_value(value)

        return self._nominal_value

    def get_value(self):
        return self._nominal_value

    def control_shutter(self, open_state):
        """Opens or closses shutter

        :param open_state: open state
        :type open_state: bool
        :return: None
        """
        if open_state:
            if self._nominal_value == self.VALUES.CLOSED:
                self.open()
        else:
            if self._nominal_value == self.VALUES.OPEN:
                self.close()

    def _set_value(self, value):
        if value == self.VALUES.OPEN:
            self.cmd_open()
        elif value == self.VALUES.CLOSED:
            self.cmd_close()

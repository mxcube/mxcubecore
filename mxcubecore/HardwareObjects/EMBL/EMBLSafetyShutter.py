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

from mxcubecore.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLSafetyShutter(Device):
    """
    EMBLSafetyShutter defines interface to DESY ics
    """

    shutter_state_list = {
        3: "unknown",
        1: "closed",
        0: "opened",
        9: "moving",
        17: "automatic",
        23: "fault",
        46: "disabled",
        -1: "error",
    }

    def __init__(self, name):
        Device.__init__(self, name)

        self.use_shutter = None
        self.data_collection_state = None
        self.shutter_can_open = None
        self.shutter_state = None
        self.shutter_state_open = None
        # GB 20190304: per misteriously disappearing first update of
        # shutter_state_closed:
        self.shutter_state_closed = True
        self.shutter_can_open = None

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

        self.ics_enabled = None
        self.use_shutter = None
        self.getWagoState = self.getShutterState

    def init(self):
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

    def connected(self):
        """
        Sets is ready
        :return:
        """
        self.set_is_ready(True)

    def disconnected(self):
        """
        Sets not ready
        :return:
        """
        self.set_is_ready(False)

    def data_collection_state_changed(self, state):
        """Updates shutter state when data collection state changes

        :param state: data collection state
        :type state: str
        :return: None
        """
        self.data_collection_state = state
        self.getShutterState()

    def state_open_changed(self, state):
        """Updates shutter state when shutter open value changes

        :param state: shutter open state
        :type state: str
        :return: None
        """

        self.shutter_state_open = state
        self.getShutterState()

    def state_closed_changed(self, state):
        """Updates shutter state when shutter close value changes

        :param state: shutter close state
        :type state: str
        :return: None
        """
        self.shutter_state_closed = state
        self.getShutterState()

    def state_open_permission_changed(self, state):
        """Updates shutter state when open permission changes

        :param state: permission state
        :type state: str
        :return: None
        """
        self.shutter_can_open = state
        self.getShutterState()

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
        self.getShutterState()

    def getShutterState(self):
        """Updates shutter state

        :return: shutter state as str
        """
        msg = ""

        if self.data_collection_state == "collecting":
            self.shutter_state = "disabled"
        elif self.shutter_state_open:
            self.shutter_state = "opened"
        elif self.shutter_state_closed:
            self.shutter_state = "closed"
        elif not self.shutter_can_open:
            self.shutter_state = "disabled"
        else:
            self.shutter_state = "unknown"

        if not self.shutter_state_open and not self.shutter_can_open:
            self.shutter_state = "noperm"
            msg = "No permission"

        if not self.ics_enabled:
            self.shutter_state = "disabled"
            msg = "Ics broke"

        if not self.use_shutter:
            self.shutter_state = self.shutter_state_list[0]

        self.emit("shutterStateChanged", (self.shutter_state, msg))

        return self.shutter_state

    def is_opened(self):
        """
        Returns True if shutter is opened
        :return:
        """
        return self.shutter_state_open

    def openShutter(self):
        """Opens shutter
           set the shutter open command to any TEXT value of size 1 to open it

        :return: None
        """
        if not self.use_shutter:
            logging.getLogger("HWR").info("Safety shutter is disabled")
        else:
            self.control_shutter(True)

    def closeShutter(self):
        """Closes shutter
           set the shutter close command to any TEXT value of size 1 to open it

        :return: None
        """
        self.control_shutter(False)

    def control_shutter(self, open_state):
        """Opens or closses shutter

        :param open_state: open state
        :type open_state: bool
        :return: None
        """
        if open_state:
            if self.shutter_state == "closed":
                self.open_shutter()
        else:
            if self.shutter_state == "opened":
                self.close_shutter()

    def close_shutter(self):
        """Closes shutter

        :return: None
        """
        logging.getLogger("HWR").info("Safety shutter: Closing beam shutter...")
        try:
            self.cmd_close()
        except Exception:
            logging.getLogger("GUI").error("Safety shutter: unable to close shutter")

    def open_shutter(self):
        """Opens shutter

        :return:
        """
        logging.getLogger("HWR").info("Safety shutter: Openning beam shutter...")
        try:
            self.cmd_open()
        except Exception:
            logging.getLogger("GUI").error("Safety shutter: unable to open shutter")

    def re_emit_values(self):
        """Reemits all signals

        :return: None
        """
        self.getShutterState()

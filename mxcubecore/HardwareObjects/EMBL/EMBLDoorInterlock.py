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

import logging
import gevent
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLDoorInterlock(HardwareObject):

    DoorInterlockState = {
        3: "unlocked",
        1: "closed",
        0: "locked_active",
        46: "locked_inactive",
        -1: "error",
    }

    def __init__(self, name):

        Device.__init__(self, name)

        self.use_door_interlock = None
        self.door_interlock_state = None
        self.door_interlock_final_state = None
        self.door_interlock_breakabled = None

        self.chan_ics_error = None
        self.chan_state_locked = None
        self.chan_state_breakable = None
        self.chan_cmd_break_error = None
        self.cmd_break_interlock = None

        self.ics_enabled = True

    def init(self):

        self.door_interlock_state = "unknown"

        self.use_door_interlock = self.get_property("useDoorInterlock", True)

        self.chan_state_locked = self.get_channel_object("chanStateLocked")
        self.chan_state_locked.connect_signal("update", self.state_locked_changed)
        self.chan_state_breakable = self.get_channel_object("chanStateBreakable")
        self.chan_state_breakable.connect_signal("update", self.state_breakable_changed)

        self.chan_ics_error = self.get_channel_object("chanIcsErrorOne")
        self.chan_ics_error.connect_signal("update", self.ics_error_msg_changed)

        self.chan_cmd_break_error = self.get_channel_object("chanCmdBreakError")
        if self.chan_cmd_break_error is not None:
            self.chan_cmd_break_error.connect_signal(
                "update", self.cmd_break_error_msg_changed
            )

        self.cmd_break_interlock = self.get_command_object("cmdBreak")

    def cmd_break_error_msg_changed(self, error_msg):
        """Displays error log message if door interlock break do not work

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0:
            logging.getLogger("GUI").error(
                "Break ICS door interlock: Error %s" % error_msg
            )

    def ics_error_msg_changed(self, error_msg):
        """Updates ICS error message

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0:
            self.ics_enabled = False
        else:
            self.ics_enabled = True
        self.get_state()

    def connected(self):
        """Sets is ready"""
        self.set_is_ready(True)

    def disconnected(self):
        """Sets not ready"""
        self.set_is_ready(False)

    def state_breakable_changed(self, state):
        """Updates door interlock state"""
        self.door_interlock_breakabled = state
        self.get_state()

    def state_locked_changed(self, state):
        """Updates door interlock state"""
        self.door_interlock_state = state
        self.get_state()

    def get_state(self):
        """Returns current state"""
        if self.door_interlock_state:
            if self.door_interlock_breakabled:
                self.door_interlock_final_state = "locked_active"
                msg = "Locked (unlock enabled)"
            else:
                self.door_interlock_final_state = "locked_inactive"
                msg = "Locked (unlock disabled)"
        else:
            self.door_interlock_final_state = "unlocked"
            msg = "Unlocked"

        if not self.ics_enabled:
            self.door_interlock_final_state = "error"
            msg = "Desy ICS error"

        if not self.use_door_interlock:
            self.door_interlock_final_state = "locked_active"
            msg = "Locked (unlock enabled)"

        self.emit("doorInterlockStateChanged", self.door_interlock_final_state, msg)
        return self.door_interlock_final_state, msg

    def unlock_door_interlock(self):
        """Break Interlock (only if it is allowed by doorInterlockCanUnlock)
           It doesn't matter what we are sending in the command
           as long as it is a one char
        """
        if HWR.beamline.diffractometer is not None:
            detector_distance = HWR.beamline.detector.distance
            if HWR.beamline.diffractometer.in_plate_mode():
                if detector_distance is not None:
                    if detector_distance.get_value() < 780:
                        detector_distance.set_value(800, timeout=None)
                        while detector_distance.get_value() < 360:
                            gevent.sleep(0.01)
                        gevent.sleep(2)
            else:
                if detector_distance is not None:
                    if detector_distance.get_value() < 1099:
                        detector_distance.set_value(1100)
                        gevent.sleep(1)
            try:
                HWR.beamline.diffractometer.set_phase(
                    HWR.beamline.diffractometer.PHASE_TRANSFER, timeout=None
                )
            except Exception:
                logging.getLogger("GUI").error(
                    "Unable to set diffractometer to transfer phase"
                )

        if not self.use_door_interlock:
            logging.getLogger().info("Door interlock is disabled")
            return

        if self.door_interlock_state:
            if self.door_interlock_breakabled:
                if self.cmd_break_interlock is None:
                    self.cmd_break_interlock = self.get_command_object(
                        "cmdBreakInterlock"
                    )
                self.cmd_break_interlock()
            else:
                msg = (
                    "Door Interlock cannot be broken at the moment "
                    + "please check its status and try again."
                )
                logging.getLogger("GUI").error(msg)
        else:
            logging.getLogger("HWR").info("Door is Interlocked")

    def re_emit_values(self):
        """Updates state"""
        self.get_state()

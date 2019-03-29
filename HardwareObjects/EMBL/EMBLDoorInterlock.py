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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import gevent
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLDoorInterlock(Device):

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

        self.detector_distance_hwobj = None
        self.diffractometer_hwobj = None

        self.before_unlock_commands_present = None
        self.before_unlock_commands = None

        self.chan_ics_error = None
        self.chan_state_locked = None
        self.chan_state_breakable = None
        self.chan_cmd_break_error = None
        self.cmd_break_interlock = None

        self.ics_enabled = True

        self.getState = self.get_state

    def init(self):

        self.door_interlock_state = "unknown"

        self.detector_distance_hwobj = self.getObjectByRole("detector_distance")
        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")

        self.before_unlock_commands_present = self.getProperty(
            "before_unlock_commands_present"
        )
        try:
            self.before_unlock_commands = eval(self.getProperty("beforeUnlockCommands"))
        except BaseException:
            pass

        self.use_door_interlock = self.getProperty("useDoorInterlock")
        if self.use_door_interlock is None:
            self.use_door_interlock = True

        self.chan_state_locked = self.getChannelObject("chanStateLocked")
        self.chan_state_locked.connectSignal("update", self.state_locked_changed)
        self.chan_state_breakable = self.getChannelObject("chanStateBreakable")
        self.chan_state_breakable.connectSignal("update", self.state_breakable_changed)

        self.chan_ics_error = self.getChannelObject("chanIcsErrorOne")
        self.chan_ics_error.connectSignal("update", self.ics_error_msg_changed)

        self.chan_cmd_break_error = self.getChannelObject("chanCmdBreakError")
        if self.chan_cmd_break_error is not None:
            self.chan_cmd_break_error.connectSignal(
                "update", self.cmd_break_error_msg_changed
            )

        self.cmd_break_interlock = self.getCommandObject("cmdBreak")

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
        self.setIsReady(True)

    def disconnected(self):
        """Sets not ready"""
        self.setIsReady(False)

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
        if self.diffractometer_hwobj is not None:
            if self.diffractometer_hwobj.in_plate_mode():
                if self.detector_distance_hwobj is not None:
                    if self.detector_distance_hwobj.getPosition() < 780:
                        self.detector_distance_hwobj.move(800, timeout=None)
                        while self.detector_distance_hwobj.getPosition() < 360:
                            gevent.sleep(0.01)
                        gevent.sleep(2)
            else:
                if self.detector_distance_hwobj is not None:
                    if self.detector_distance_hwobj.getPosition() < 1099:
                        self.detector_distance_hwobj.move(1100)
                        gevent.sleep(1)
            try:
                self.diffractometer_hwobj.set_phase(
                    self.diffractometer_hwobj.PHASE_TRANSFER, timeout=None
                )
            except BaseException:
                logging.getLogger("GUI").error(
                    "Unable to set diffractometer to transfer phase"
                )

        if not self.use_door_interlock:
            logging.getLogger().info("Door interlock is disabled")
            return

        if self.door_interlock_state:
            if self.door_interlock_breakabled:
                if self.cmd_break_interlock is None:
                    self.cmd_break_interlock = self.getCommandObject(
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

    def update_values(self):
        """Updates state"""
        self.get_state()

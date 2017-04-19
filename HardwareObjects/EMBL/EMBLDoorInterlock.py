#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import gevent
from HardwareRepository.BaseHardwareObjects import Device

import _tine as tine


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLDoorInterlock(Device):

    DoorInterlockState = {3: 'unlocked',
                          1: 'closed',
                          0: 'locked_active',
                          46: 'locked_inactive',
                          -1: 'error'
                         }

    def __init__(self, name):

        Device.__init__(self, name)

        self.use_door_interlock = None
        self.door_interlock_state = None
        self.door_interlock_final_state = None
        self.door_interlock_breakabled = None

        self.detector_distance_hwobj = None

        self.before_unlock_commands_present = None
        self.before_unlock_commands = None

        self.chan_state_locked = None
        self.chan_state_breakable = None
        self.cmd_break_interlock = None

    def init(self):
        self.door_interlock_state = "unknown"

        self.detector_distance_hwobj = \
            self.getObjectByRole("detector_distance")

        self.before_unlock_commands_present = \
            self.getProperty("before_unlock_commands_present")
        self.before_unlock_commands = eval(self.getProperty("beforeUnlockCommands"))

        self.use_door_interlock = self.getProperty('useDoorInterlock')
        if self.use_door_interlock is None:
            self.use_door_interlock = True

        self.chan_state_locked = self.getChannelObject('chanStateLocked')
        self.chan_state_locked.connectSignal('update', self.state_locked_changed)
        self.chan_state_breakable = self.getChannelObject('chanStateBreakable')
        self.chan_state_breakable.connectSignal('update', self.state_breakable_changed)

        self.cmd_break_interlock = self.getCommandObject('cmdBreak')

        self.getState = self.get_state

    def connected(self):
        """Sets is ready"""
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def state_breakable_changed(self, state):
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
                self.door_interlock_final_state = 'locked_active'
                msg = "Locked (unlock enabled)"
            else:
                self.door_interlock_final_state = 'locked_inactive'
                msg = "Locked (unlock disabled)"
        else:
            self.door_interlock_final_state = 'unlocked'
            msg = "Unlocked"

        if not self.use_door_interlock:
            self.door_interlock_final_state = 'locked_active'
            msg = "Locked (unlock enabled)"

        self.emit('doorInterlockStateChanged', self.door_interlock_final_state, msg)
        return self.door_interlock_final_state, msg

    def unlock_door_interlock(self):
        """Break Interlock (only if it is allowed by doorInterlockCanUnlock)
           It doesn't matter what we are sending in the command
           as long as it is a one char
        """
        if self.detector_distance_hwobj.getPosition() < 340:
            self.detector_distance_hwobj.move(500)
            gevent.sleep(1)

        if not self.use_door_interlock:
            logging.getLogger().info('Door interlock is disabled')
            return

        if self.door_interlock_state:
            gevent.spawn(self.unlock_doors_thread)
        else:
            logging.getLogger().info('Door is Interlocked')

    def before_unlock_actions(self):
        """Executes some commands bedore unlocking the doors"""
        for command in self.before_unlock_commands:
            addr = command["address"]
            prop = command["property"]
            if len(command["argument"]) == 0:
                arg = [0]
            else:
                try:
                    arg = [eval(command["argument"])]
                except:
                    arg = [command["argument"]]
            if command["type"] == "set":
                tine.set(addr, prop, arg)
            elif command["type"] == "query":
                tine.query(addr, prop, arg[0])

    def unlock_doors_thread(self):
        """Gevent method to unlock the doors"""
        if self.door_interlock_breakabled:
            try:
                self.before_unlock_actions()
            except:
                pass
            if self.cmd_break_interlock is None:
                self.cmd_break_interlock = self.getCommandObject('cmdBreakInterlock')
            self.cmd_break_interlock()
        else:
            msg = "Door Interlock cannot be broken at the moment " + \
                  "please check its status and try again."
            logging.getLogger("user_level_log").error(msg)

    def update_values(self):
        self.get_state()

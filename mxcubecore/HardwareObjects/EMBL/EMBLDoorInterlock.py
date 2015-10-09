import logging
import gevent
from HardwareRepository.BaseHardwareObjects import Device

import _tine as tine

class EMBLDoorInterlock(Device):
    DoorInterlockState = {
        3: 'unlocked',
        1: 'closed',
        0: 'locked_active',
        46: 'locked_inactive',
        -1: 'error'
        }

    def __init__(self, name):
        Device.__init__(self, name)   
           
    def init(self):
        self.door_interlock_state = "unknown"

        self.door_interlocked_cond_value = None
        self.door_interlocked_cond = str(self.getProperty("doorInterlockedCond"))

        self.can_unlock_cond_value = None
        self.can_unlock_cond = int(self.getProperty("canUnlockCond"))
        self.door_interlocked_cond_value = None
        self.door_interlocked_cond = int(self.getProperty("doorInterlockedCond"))

        self.beforeUnlockCommandsPresent = self.getProperty("beforeUnlockCommandsPresent")
        if self.beforeUnlockCommandsPresent:
           self.beforeUnlockCommands = self.getProperty("beforeUnlockCommands")

        self.use_door_interlock = self.getProperty('useDoorInterlock')
        if self.use_door_interlock is None:
            self.use_door_interlock = True

        self.cmd_break_interlock = self.getCommandObject('cmdBreakInterlock')
        self.chan_can_unlock_cond = self.getChannelObject('chanCanUnlockCond')
        if self.chan_can_unlock_cond is not None: 
            self.chan_can_unlock_cond.connectSignal('update', self.can_unlock_cond_changed)
        self.chan_door_is_interlocked = self.getChannelObject('chanDoorInterlocked')
        if self.chan_door_is_interlocked is not None:
            self.chan_door_is_interlocked.connectSignal('update', self.door_interlock_state_changed)

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def can_unlock_cond_changed(self, state):
        self.can_unlock_cond_value = int(state)
        self.get_state()

    def door_interlock_state_changed(self, state):
        value = self.door_interlocked_cond_value
        self.door_interlocked_cond_value = int(state)
        #if (value != self.door_interlocked_cond_value):
        self.get_state()

    def door_interlock_can_unlock(self):
        #self.can_unlock_cond_value = self.chan_can_unlock_cond.getValue()
        return self.can_unlock_cond == self.can_unlock_cond_value

    def door_is_interlocked(self):
        #self.door_interlocked_cond_value = self.chan_door_is_interlocked.getValue()
        return self.door_interlocked_cond == self.door_interlocked_cond_value 

    def getState(self):
        return self.door_interlock_state 

    def get_state(self): 
        if self.door_is_interlocked():
            if self.door_interlock_can_unlock():
                self.door_interlock_state = 'locked_active' 
                msg = "Locked (unlock enabled)"
            else:
                self.door_interlock_state = 'locked_inactive' 
                msg = "Locked (unlock disabled)"
	else:
            self.door_interlock_state = 'unlocked'
            msg = "Unlocked"

        if not self.use_door_interlock:
            self.door_interlock_state = 'locked_active'
            msg = "Locked (unlock enabled)"

        self.emit('doorInterlockStateChanged', self.door_interlock_state, msg)
        return self.door_interlock_state

    #  Break Interlock (only if it is allowed by doorInterlockCanUnlock) 
    #  It doesn't matter what we are sending in the command as long as it is a one char
    def unlock_door_interlock(self):
        if not self.use_door_interlock:
            logging.getLogger().info('Door interlock is disabled')
            return

        if self.door_is_interlocked():
           gevent.spawn(self.unlock_doors_thread)
        else:
            logging.getLogger().info('Door is Interlocked')
        
    def before_unlock_actions(self):
	if self.beforeUnlockCommandsPresent:
            for command in eval(self.beforeUnlockCommands):
                addr = command["address"]
                prop =  command["property"]
                if len(command["argument"]) == 0:
                    arg = [0]
                else:
                    try:
                        arg = [eval(command["argument"])]
                    except :
                        arg = [command["argument"]]
                if command["type"] == "set" :
                    tine.set(addr,prop,arg)	
                elif command["type"] == "query" :
                    tine.query(addr,prop,arg[0])

    def unlock_doors_thread(self):
        if self.door_interlock_can_unlock():
           try:
              self.before_unlock_actions()
              if self.cmd_break_interlock is None:
                  self.cmd_break_interlock = self.getCommandObject('cmdBreakInterlock') 
              self.cmd_break_interlock("b")
           except:
              logging.getLogger().error('Door interlock: unable to break door interlock.')
        else:
            msg = "Door Interlock cannot be broken at the moment " + \
                  "please check its status and try again."
            logging.getLogger("user_level_log").error(msg)

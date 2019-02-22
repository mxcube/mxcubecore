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

from HardwareRepository import BaseHardwareObjects

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"

STATE_OUT, STATE_IN, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = \
    (0, 1, 9, 11, 13, 23)


class ALBAFastShutter(BaseHardwareObjects.Device):

    states = {
        STATE_OUT: "out",
        STATE_IN: "in",
        STATE_MOVING: "moving",
        STATE_FAULT: "fault",
        STATE_ALARM: "alarm",
        STATE_UNKNOWN: "unknown",
    }

    default_state_strings = ["Out", "In"]

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

        self.cmd_ni_start = None
        self.cmd_ni_stop = None

        self.chan_actuator = None
        self.chan_motor_pos = None
        self.chan_motor_state = None

        self.actuator_state = STATE_UNKNOWN
        self.actuator_value = None
        self.motor_position = None
        self.motor_state = None
        self.state_strings = None

    def init(self):

        try:
            self.cmd_ni_start = self.getCommandObject("nistart")
            self.cmd_ni_stop = self.getCommandObject("nistop")

            self.chan_actuator = self.getChannelObject('actuator')
            self.chan_motor_pos = self.getChannelObject('motorposition')
            self.chan_motor_state = self.getChannelObject('motorstate')

            self.chan_actuator.connectSignal('update', self.stateChanged)
            self.chan_motor_pos.connectSignal('update', self.motorPositionChanged)
            self.chan_motor_state.connectSignal('update', self.motorStateChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot report FrontEnd State', self.name())

        try:
            state_string = self.getProperty("states")
            if state_string is None:
                self.state_strings = self.default_state_strings
            else:
                states = state_string.split(",")
                self.state_strings = states[1].strip(), states[0].strip()
        except BaseException:
            import traceback
            logging.getLogger("HWR").warning(traceback.format_exc())
            self.state_strings = self.default_state_strings

    def getState(self):
        if self.actuator_state == STATE_UNKNOWN:
            self.actuator_value = self.chan_actuator.getValue()
            self.motor_position = self.chan_motor_pos.getValue()
            self.motor_state = self.chan_motor_state.getValue()
            self.update_state()
        return self.actuator_state

    def update_state(self):

        if None in [self.actuator_value, self.motor_position, self.motor_state]:
            act_state = STATE_UNKNOWN
        elif str(self.motor_state) == "MOVING":
            act_state = STATE_MOVING
        elif str(self.motor_state) != "ON" or abs(self.motor_position) > 0.01:
            act_state = STATE_ALARM
        else:
            state = self.actuator_value.lower()

            if state == 'high':
                act_state = STATE_OUT
            else:
                act_state = STATE_IN

        if act_state != self.actuator_state:
            self.actuator_state = act_state
            self.emitStateChanged()

    def stateChanged(self, value):
        self.actuator_value = value
        self.update_state()

    def motorPositionChanged(self, value):
        self.motor_position = value
        self.update_state()

    def motorStateChanged(self, value):
        self.motor_state = value
        self.update_state()

    def emitStateChanged(self):
        self.emit('fastStateChanged', (self.actuator_state,))

    def getMotorPosition(self):
        if self.motor_position is None:
            self.motor_position = self.chan_motor_pos.getValue()
        return self.motor_position

    def getMotorState(self):
        if self.motor_state is None:
            self.motor_state = self.chan_motor_state.getValue()
        return self.motor_state

    def getUserName(self):
        return self.username

    def getStatus(self):
        state = self.getState()

        if state in [STATE_OUT, STATE_IN]:
            return self.state_strings[state]
        elif state in self.states:
            return self.states[state]
        else:
            return "Unknown"

    def cmdIn(self):
        self.open()

    def cmdOut(self):
        self.close()

    # TODO: Review, it is called twice after a collection (already in motion problem)
    def close(self):
        logging.getLogger('HWR').debug("Closing the fast shutter")
        logging.getLogger('HWR').debug("value = %s, state = %s" %
                                       (self.chan_motor_pos.getValue(),
                                        self.actuator_state))
        if abs(self.chan_motor_pos.getValue()) > 0.01:
            self.chan_motor_pos.setValue(0)
        self.set_ttl('High')

    def open(self):
        logging.getLogger('HWR').debug("Opening the fast shutter")
        logging.getLogger('HWR').debug("value = %s, state = %s" %
                                       (self.chan_motor_pos.getValue(),
                                        self.actuator_state))

        if abs(self.chan_motor_pos.getValue()) > 0.01:
            self.chan_motor_pos.setValue(0)
        self.set_ttl('Low')

    def set_ttl(self, value):
        self.cmd_ni_stop()
        self.chan_actuator.setValue(value)
        self.cmd_ni_start()

    def is_open(self):
        if self.actuator_state == STATE_IN:
            return True
        else:
            return False

    def is_close(self):
        if self.actuator_state == STATE_OUT:
            return True
        else:
            return False


def test_hwo(hwo):
    print "Name is: ", hwo.getUserName()

    print "Shutter state is: ", hwo.getState()
    print "Shutter status is: ", hwo.getStatus()
    print "Motor position is: ", hwo.getMotorPosition()
    print "Motor state is: ", hwo.getMotorState()

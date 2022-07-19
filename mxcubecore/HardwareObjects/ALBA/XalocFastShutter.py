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

"""
[Name] XalocFastShutter

[Description]
HwObj used to operate the Fast Shutter

[Signals]
- fastStateChanged
"""

from __future__ import print_function

import logging
import time

from mxcubecore import BaseHardwareObjects
from taurus.core.tango.enums import DevState


__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"

STATE_OUT, STATE_IN, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = \
    (0, 1, 9, 11, 13, 23)


class XalocFastShutter(BaseHardwareObjects.Device):
    """
    Shutter IN: motor position is 0 and IDLE state is High.
    Shutter OUT: motor position is 0 and IDLE state is Low.
    Shutter Fault: motor position is not 0.
    """

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
        self.logger = logging.getLogger("HWR.XalocFastShutter")
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
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        try:
            self.cmd_ni_start = self.get_command_object("nistart")
            self.cmd_ni_stop = self.get_command_object("nistop")

            self.chan_actuator = self.get_channel_object('actuator')
            self.chan_motor_pos = self.get_channel_object('motorposition')
            self.chan_motor_state = self.get_channel_object('motorstate')

            self.chan_actuator.connect_signal('update', self.state_changed)
            self.chan_motor_pos.connect_signal('update', self.motor_position_changed)
            self.chan_motor_state.connect_signal('update', self.motor_state_changed)
        except Exception:
            self.logger.warning('Error when initilaizing')

        try:
            state_string = self.get_property("states")
            if state_string is None:
                self.state_strings = self.default_state_strings
            else:
                states = state_string.split(",")
                self.state_strings = states[1].strip(), states[0].strip()
        except Exception as e:
            self.logger.warning("%s" % str(e))
            self.state_strings = self.default_state_strings

    def get_state(self):
        if self.actuator_state == STATE_UNKNOWN:
            self.actuator_value = self.chan_actuator.get_value()
            self.motor_position = self.chan_motor_pos.get_value()
            self.motor_state = self.chan_motor_state.get_value()
            self.update_state(value)
        return self.actuator_state

    def update_state(self, state_unused):

        if None in [self.actuator_value, self.motor_position, self.motor_state]:
            act_state = STATE_UNKNOWN
        elif self.motor_state == DevState.MOVING:
            act_state = STATE_MOVING
        elif self.motor_state != DevState.ON or abs(self.motor_position) > 0.01:
            act_state = STATE_ALARM
        else:
            state = self.actuator_value.lower()

            if state == 'high':
                act_state = STATE_IN
            else:
                act_state = STATE_OUT

        if act_state != self.actuator_state:
            self.actuator_state = act_state
            self.emit_state_changed()

    def state_changed(self, value):
        self.actuator_value = value
        self.update_state(value)

    def motor_position_changed(self, value):
        self.motor_position = value
        self.update_state(value)

    def motor_state_changed(self, value):
        self.motor_state = value
        self.update_state(value)

    def emit_state_changed(self):
        self.emit('fastStateChanged', (self.actuator_state,))

    def get_motor_position(self):
        if self.motor_position is None:
            self.motor_position = self.chan_motor_pos.get_value()
        return self.motor_position

    def get_motor_state(self):
        if self.motor_state is None:
            self.motor_state = self.chan_motor_state.get_value()
        return self.motor_state

    def get_user_name(self):
        return self.username

    def get_status(self):
        state = self.getState()

        if state in [STATE_OUT, STATE_IN]:
            return self.state_strings[state]
        elif state in self.states:
            return self.states[state]
        else:
            return "Unknown"

    def cmd_in(self):
        self.open()

    def cmd_out(self):
        self.close()

    # TODO: Review, it is called twice after a collection (already in motion problem)
    def close(self):
        self.logger.debug("Closing the fast shutter")
        self.logger.debug("value = %s, state = %s" %
                                       (self.chan_motor_pos.get_value(),
                                        self.actuator_state))
        if abs(self.chan_motor_pos.get_value()) > 0.01:
            while self.getMotorState() != DevState.ON:
                time.sleep(0.5)
            # closed position is 0
            self.chan_motor_pos.set_value(0)
        self.set_ttl('High')

    def open(self):
        self.logger.debug("Opening the fast shutter")
        self.logger.debug("value = %s, state = %s" %
                                       (self.chan_motor_pos.get_value(),
                                        self.actuator_state))

        if abs(self.chan_motor_pos.get_value()) > 0.01:
            self.chan_motor_pos.set_value(0)
        self.set_ttl('Low')

    def set_ttl(self, value):
        self.cmd_ni_stop()
        self.chan_actuator.set_value(value)
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
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.getState())
    print("Shutter status is: ", hwo.getStatus())
    print("Motor position is: ", hwo.getMotorPosition())
    print("Motor state is: ", hwo.getMotorState())
    print("Is shutter open: ", hwo.is_open())
    print("Is shutter close: ", hwo.is_close())

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
[Name] XalocEpsActuator

[Description]
Tango Shutter Hardware Object

Public Interface:
   Commands:
       int get_state()
           Description:
               returns current state
           Output:
               integer value describing the state
               current states correspond to:
                      0: out
                      1: in
                      9: moving
                     11: alarm
                     13: unknown
                     23: fault

       string get_status()
           Description:
               returns current state as a string that can contain a more
               descriptive information about current state

           Output:
               status string

       cmd_in()
           Executes the command associated to the "In" action
       cmd_out()
           Executes the command associated to the "Out" action

   [Signals]
       stateChanged

"""

from __future__ import print_function

import logging

from mxcubecore import BaseHardwareObjects

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"

STATE_IN, STATE_OUT, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = \
    (0, 1, 9, 11, 13, 23)


class XalocEpsActuator(BaseHardwareObjects.Device):

    states = {
        STATE_OUT: "out",
        STATE_IN: "in",
        STATE_MOVING: "moving",
        STATE_FAULT: "fault",
        STATE_ALARM: "alarm",
        STATE_UNKNOWN: "unknown",
    }

    default_state_strings = ["In", "Out"]

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocEpsActuator")
        self.chan_actuator = None

        self.actuator_state = None
        self.state_strings = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.actuator_state = STATE_UNKNOWN

        try:
            self.chan_actuator = self.get_channel_object("actuator")
            self.chan_actuator.connect_signal("update", self.state_changed)
        except KeyError:
            self.logger.warning('Cannot report EPS Actuator State for %s' % self.name())

        try:
            state_string = self.get_property("states")
            if state_string is None:
                self.state_strings = self.default_state_strings
            else:
                self.state_strings = state_string.split(",")
        except Exception as e:
            self.logger.warning("%s" % str(e))
            self.state_strings = self.default_state_strings

    def get_state(self):
        self.actuator_state = self.chan_actuator.force_get_value()
        return self.actuator_state

    def state_changed(self, value):
        self.actuator_state = value
        self.logger.debug("State change for actuator %s, new state is %s" % (self.name(), value) )
        self.emit('stateChanged', (self.actuator_state,))

    def get_user_name(self):
        return self.username

    def get_status(self):
        """
        """
        state = self.get_state()

        if state in [STATE_OUT, STATE_IN]:
            return self.state_strings[state]
        elif state in self.states:
            return self.states[state]
        else:
            return "Unknown"

    def open(self):
        self.cmd_out()

    def close(self):
        self.cmd_in()

    def cmd_in(self):
        self.chan_actuator.set_value( STATE_IN )

    def cmd_out(self):
        self.chan_actuator.set_value( STATE_OUT )

def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.get_state())
    print("Shutter status is: ", hwo.get_status())

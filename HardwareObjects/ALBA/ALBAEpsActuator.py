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
[Name] ALBAEnergy

[Description]
Tango Shutter Hardware Object

Public Interface:
   Commands:
       int getState()
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

       string getStatus()
           Description:
               returns current state as a string that can contain a more
               descriptive information about current state

           Output:
               status string

       cmdIn()
           Executes the command associated to the "In" action
       cmdOut()
           Executes the command associated to the "Out" action

   [Signals]
       stateChanged

"""

from __future__ import print_function

import logging

from HardwareRepository import BaseHardwareObjects

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"

STATE_OUT, STATE_IN, STATE_MOVING, STATE_FAULT, STATE_ALARM, STATE_UNKNOWN = \
    (0, 1, 9, 11, 13, 23)


class ALBAEpsActuator(BaseHardwareObjects.Device):

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

        self.chan_actuator = None

        self.actuator_state = None
        self.state_strings = None

    def init(self):
        self.actuator_state = STATE_UNKNOWN

        try:
            self.chan_actuator = self.getChannelObject('actuator')
            self.chan_actuator.connectSignal('update', self.stateChanged)
        except KeyError:
            logging.getLogger().warning('%s: cannot report EPS Actuator State',
                                        self.name())

        try:
            state_string = self.getProperty("states")
            if state_string is None:
                self.state_strings = self.default_state_strings
            else:
                states = state_string.split(",")
                self.state_strings = states[1].strip(), states[0].strip()
        except Exception as e:
            logging.getLogger("HWR").warning("%s" % str(e))
            self.state_strings = self.default_state_strings

    def getState(self):
        state = self.chan_actuator.getValue()
        self.actuator_state = self.convert_state(state)
        return self.actuator_state

    def convert_state(self, state):
        if state == 0:
            act_state = STATE_OUT
        elif state == 1:
            act_state = STATE_IN
        else:
            act_state = STATE_UNKNOWN
        return act_state

    def stateChanged(self, value):
        self.actuator_state = self.convert_state(value)
        self.emit('stateChanged', (self.actuator_state,))

    def getUserName(self):
        return self.username

    def getStatus(self):
        """
        """
        state = self.getState()

        if state in [STATE_OUT, STATE_IN]:
            return self.state_strings[state]
        elif state in self.states:
            return self.states[state]
        else:
            return "Unknown"

    def open(self):
        self.cmdIn()

    def close(self):
        self.cmdOut()

    def cmdIn(self):
        self.chan_actuator.setValue(1)

    def cmdOut(self):
        self.chan_actuator.setValue(0)


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.getState())
    print("Shutter status is: ", hwo.getStatus())

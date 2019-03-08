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

"""
[Name]
ALBAZoomMotor

[Description]
Hardware Object is used to manipulate the zoom of the OAV camera.

[Emitted signals]
- stateChanged
- predefinedPositionChanged
"""

from __future__ import print_function

import logging

from HardwareRepository import BaseHardwareObjects
from taurus.core.tango.enums import DevState

__credits__ = ["ALBA"]
__version__ = "2.3."
__category__ = "General"


class ALBAZoomMotor(BaseHardwareObjects.Device):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.chan_position = None
        self.chan_state = None
        self.chan_labels = None

        self.current_position = 0
        self.current_state = None

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor IOR")
        self.chan_position = self.getChannelObject("position")
        self.chan_state = self.getChannelObject("state")
        self.chan_labels = self.getChannelObject("labels")

        self.chan_position.connectSignal("update", self.positionChanged)
        self.chan_state.connectSignal("update", self.stateChanged)

    def getPredefinedPositionsList(self):
        labels = self.chan_labels.getValue()
        labels = labels.split()
        retlist = []
        for label in labels:
            pos = str(label.replace(":", " "))
            retlist.append(pos)
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        new_retlist = []
        for n, e in enumerate(retlist):
            name = e.split()
            new_retlist.append("%s %s" % (n + 1, name[0]))
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(new_retlist))
        return new_retlist

    def moveToPosition(self, posno):
        no = posno.split()[0]
        logging.getLogger("HWR").debug("type %s" % type(no))
        logging.getLogger("HWR").debug("Moving to position %s" % no)
        state = self.chan_position.setValue(int(no))

    def motorIsMoving(self):
        if str(self.getState()) == "MOVING":
            return True
        else:
            return False

    def getLimits(self):
        return 1, 12

    def getState(self):
        state = self.chan_state.getValue()
        curr_pos = self.getPosition()
        if state == DevState.ON:
            return ALBAZoomMotor.READY
        elif state == DevState.MOVING or state == DevState.RUNNING:
            return ALBAZoomMotor.MOVING
        elif curr_pos in self.getLimits():
            return ALBAZoomMotor.ONLIMIT
        else:
            return ALBAZoomMotor.FAULT

    def getPosition(self):
        try:
            return self.chan_position.getValue()
        except Exception as e:
            return self.current_position

    def getCurrentPositionName(self):
        try:
            n = int(self.chan_position.getValue())
            value = "%s z%s" % (n, n)
            logging.getLogger("HWR").debug("getCurrentPositionName: %s" % repr(value))
            return value
        except Exception as e:
            logging.getLogger("HWR").debug("cannot get name zoom value\n%s" % str(e))
            return None

    def stateChanged(self, state):
        logging.getLogger("HWR").debug("stateChanged emitted: %s" % state)
        the_state = self.getState()
        if the_state != self.current_state:
            self.current_state = the_state
            self.emit('stateChanged', (the_state, ))

    def positionChanged(self, currentposition):
        previous_position = self.current_position
        self.current_position = self.getCurrentPositionName()
        if self.current_position != previous_position:
            logging.getLogger("HWR").debug(
                "predefinedPositionChanged emitted: %s" %
                self.current_position)
            self.emit('predefinedPositionChanged', (self.current_position, 0))

    def isReady(self):
        state = self.getState()
        return state == ALBAZoomMotor.READY


def test_hwo(zoom):
    print("Zoom position is : ", zoom.getPosition())
    print("Zoom position name is : ", zoom.getCurrentPositionName())
    print("Moving : ", zoom.motorIsMoving())
    print("State : ", zoom.getState())
    print("Positions : ", zoom.getPredefinedPositionsList())

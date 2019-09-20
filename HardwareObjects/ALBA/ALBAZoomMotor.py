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

[Channels]
- position
- state
- labels

[Commands]

[Emited signals]
- stateChanged
- predefinedPositionChanged

[Functions]
- None

[Included Hardware Objects]
- None

Example Hardware Object XML file :
==================================
<device class="ALBAZoomMotor">
  <username>Zoom</username>
  <taurusname>ioregister/eh_zoom_tangoior_ctrl/2</taurusname>
  <alias>zoom</alias>
  <motor_name>Zoom</motor_name>
  <channel type="sardana" polling="200" name="position">Value</channel>
  <channel type="sardana" polling="200" name="state">State</channel>
  <channel type="sardana" name="labels">Labels</channel>
  <interval>200</interval>
  <threshold>0.001</threshold>
</device>
"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository import BaseHardwareObjects
import logging
import os
import PyTango

__author__ = "Bixente Rey"
__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAZoomMotor(BaseHardwareObjects.Device):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor IOR")
        self.positionChannel = self.getChannelObject("position")
        self.stateChannel = self.getChannelObject("state")
        self.labelsChannel = self.getChannelObject("labels")
        self.currentposition = 0
        self.currentstate = None

        self.positionChannel.connectSignal("update", self.positionChanged)
        self.stateChannel.connectSignal("update", self.stateChanged)

    def getPredefinedPositionsList(self):
        labels = self.labelsChannel.getValue()
        labels = labels.split()
        retlist = []
        for label in labels:
            #    label, pos = label.split(":")
            #    retlist.append(int(pos))
            pos = str(label.replace(":", " "))
            retlist.append(pos)
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        new_retlist = []
        for n, e in enumerate(retlist):
            name = e.split()
            new_retlist.append("%s %s" % (n + 1, name[0]))
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(new_retlist))

        # retlist = ["z1 1","z2 2"]
        # logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        return new_retlist

    def moveToPosition(self, posno):
        no = posno.split()[0]
        logging.getLogger("HWR").debug("type %s" % type(no))
        #        no = posno
        logging.getLogger("HWR").debug("Moving to position %s" % no)
        state = self.positionChannel.setValue(int(no))

    def motorIsMoving(self):
        if str(self.getState()) == "MOVING":
            return True
        else:
            return False

    def getLimits(self):
        return (1, 12)

    def getState(self):
        state = self.stateChannel.getValue()
        curr_pos = self.getPosition()
        if state == PyTango.DevState.ON:
            return ALBAZoomMotor.READY
        elif state == PyTango.DevState.MOVING or state == PyTango.DevState.RUNNING:
            return ALBAZoomMotor.MOVING
        elif curr_pos in self.getLimits():
            return ALBAZoomMotor.ONLIMIT
        else:
            return ALBAZoomMotor.FAULT
        return state

    def getPosition(self):
        try:
            return self.positionChannel.getValue()
        except BaseException:
            return self.currentposition

    def getCurrentPositionName(self):
        try:
            n = int(self.positionChannel.getValue())
            value = "%s z%s" % (n, n)
            logging.getLogger("HWR").debug("getCurrentPositionName: %s" % repr(value))
            return value
        except BaseException:
            logging.getLogger("HWR").debug("cannot get name zoom value")
            return None

    def stateChanged(self, state):
        logging.getLogger("HWR").debug("stateChanged emitted: %s" % state)
        the_state = self.getState()
        if the_state != self.currentstate:
            self.currentstate = the_state
            self.emit("stateChanged", (the_state,))

    def positionChanged(self, currentposition):
        previous_position = self.currentposition
        self.currentposition = self.getCurrentPositionName()
        if self.currentposition != previous_position:
            logging.getLogger("HWR").debug(
                "predefinedPositionChanged emitted: %s" % self.currentposition
            )
            self.emit("predefinedPositionChanged", (self.currentposition, 0))

    def isReady(self):
        state = self.getState()
        return state == ALBAZoomMotor.READY


def test_hwo(zoom):

    print(type(zoom.getState()))

    print("     Zoom position is : ", zoom.getPosition())
    print("Zoom position name is : ", zoom.getCurrentPositionName())
    print("               Moving : ", zoom.motorIsMoving())
    print("                State : ", zoom.getState())
    print("            Positions : ", zoom.getPredefinedPositionsList())


if __name__ == "__main__":
    test()

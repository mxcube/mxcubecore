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
<object class="ALBAZoomMotor">
  <username>Zoom</username>
  <taurusname>ioregister/eh_zoom_tangoior_ctrl/2</taurusname>
  <alias>zoom</alias>
  <actuator_name>Zoom</actuator_name>
  <channel type="sardana" polling="200" name="position">Value</channel>
  <channel type="sardana" polling="200" name="state">State</channel>
  <channel type="sardana" name="labels">Labels</channel>
  <interval>200</interval>
  <threshold>0.001</threshold>
</object>
"""

from mxcubecore import BaseHardwareObjects
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
import logging
import PyTango

__author__ = "Bixente Rey"
__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAZoomMotor(BaseHardwareObjects.Device, AbstractMotor):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self, name):
        super().__init__(name)

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor IOR")
        self.positionChannel = self.get_channel_object("position")
        self.stateChannel = self.get_channel_object("state")
        self.labelsChannel = self.get_channel_object("labels")
        self.currentposition = 0
        self.currentstate = None

        self.positionChannel.connect_signal("update", self.positionChanged)
        self.stateChannel.connect_signal("update", self.stateChanged)

    def get_predefined_positions_list(self):
        labels = self.labelsChannel.get_value()
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
        state = self.positionChannel.set_value(int(no))

    def motorIsMoving(self):
        if str(self.get_state()) == "MOVING":
            return True
        else:
            return False

    def get_limits(self):
        return (1, 12)

    def get_state(self):
        state = self.stateChannel.get_value()
        curr_pos = self.get_value()
        if state == PyTango.DevState.ON:
            return ALBAZoomMotor.READY
        elif state == PyTango.DevState.MOVING or state == PyTango.DevState.RUNNING:
            return ALBAZoomMotor.MOVING
        elif curr_pos in self.get_limits():
            return ALBAZoomMotor.ONLIMIT
        else:
            return ALBAZoomMotor.FAULT
        return state

    def get_value(self):
        try:
            return self.positionChannel.get_value()
        except Exception:
            return self.currentposition

    def get_current_position_name(self):
        try:
            n = int(self.positionChannel.get_value())
            value = "%s z%s" % (n, n)
            logging.getLogger("HWR").debug(
                "get_current_position_name: %s" % repr(value)
            )
            return value
        except Exception:
            logging.getLogger("HWR").debug("cannot get name zoom value")
            return None

    def stateChanged(self, state):
        logging.getLogger("HWR").debug("stateChanged emitted: %s" % state)
        the_state = self.get_state()
        if the_state != self.currentstate:
            self.currentstate = the_state
            self.emit("stateChanged", (the_state,))

    def positionChanged(self, currentposition):
        previous_position = self.currentposition
        self.currentposition = self.get_current_position_name()
        if self.currentposition != previous_position:
            logging.getLogger("HWR").debug(
                "predefinedPositionChanged emitted: %s" % self.currentposition
            )
            self.emit("predefinedPositionChanged", (self.currentposition, 0))

    def is_ready(self):
        state = self.get_state()
        return state == ALBAZoomMotor.READY


def test_hwo(zoom):

    print(type(zoom.get_state()))

    print("     Zoom position is : ", zoom.get_value())
    print("Zoom position name is : ", zoom.get_current_position_name())
    print("               Moving : ", zoom.motorIsMoving())
    print("                State : ", zoom.get_state())
    print("            Positions : ", zoom.get_predefined_positions_list())


if __name__ == "__main__":
    test()

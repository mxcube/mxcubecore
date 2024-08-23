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
ALBAZoomMotorAutoBrightness

[Description]
Hardware Object is used to manipulate the zoom IOR and the
paired backlight intensity (slave IOR)

[Channels]
- None

[Commands]

[Emited signals]
- stateChanged
- predefinedPositionChanged

[Functions]
- None

[Included Hardware Objects]
- zoom
- blight

Example Hardware Object XML file :
==================================
<object class="ALBAZoomMotorAutoBrightness">
  <object role="zoom" hwrid="/zoom"></object>
  <object role="blight" hwrid="/blight"></object>
</object>
"""

from mxcubecore import BaseHardwareObjects
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor
import logging

__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAZoomMotorAutoBrightness(BaseHardwareObjects.HardwareObject, AbstractMotor):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self, name):
        super().__init__(name)

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor autobrightness IOR")

        self.zoom = self.get_object_by_role("zoom")
        self.blight = self.get_object_by_role("blight")

        self.zoom.positionChannel.connect_signal("update", self.positionChanged)
        self.zoom.stateChannel.connect_signal("update", self.stateChanged)

    def get_predefined_positions_list(self):
        retlist = self.zoom.get_predefined_positions_list()
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        return retlist

    def moveToPosition(self, posno):
        # no = posno.split()[0]
        # logging.getLogger("HWR").debug("Moving to position %s" % no)

        # self.blight.moveToPosition(posno)
        self.zoom.moveToPosition(posno)
        state = self.zoom.get_state()
        # state = self.positionChannel.set_value(int(no))

    def motorIsMoving(self):
        return self.zoom.motorIsMoving()

    #        if str(self.get_state()) == "MOVING":
    #             return True
    #        else:
    #             return False

    def get_limits(self):
        # return (1,12)
        return self.zoom.get_limits()

    def get_state(self):
        #        state = self.stateChannel.get_value()
        #        curr_pos = self.get_value()
        #        if state == PyTango.DevState.ON:
        #             return ALBAZoomMotor.READY
        #        elif state == PyTango.DevState.MOVING or state == PyTango.DevState.RUNNING:
        #             return ALBAZoomMotor.MOVING
        #        elif curr_pos in self.get_limits():
        #             return ALBAZoomMotor.ONLIMIT
        #        else:
        #             return ALBAZoomMotor.FAULT
        #        return state
        return self.zoom.get_state()

    def get_value(self):
        return self.zoom.get_value()

    def get_current_position_name(self):
        #        n = int(self.positionChannel.get_value())
        #        value = "%s z%s" % (n, n)
        #        logging.getLogger("HWR").debug("get_current_position_name: %s" % repr(value))
        #        return value
        return self.zoom.get_current_position_name()

    def stateChanged(self, state):
        logging.getLogger("HWR").debug("stateChanged emitted: %s" % state)
        self.emit("stateChanged", (self.get_state(),))

    def positionChanged(self, currentposition):
        currentposition = self.get_current_position_name()
        logging.getLogger("HWR").debug(
            "predefinedPositionChanged emitted: %s" % currentposition
        )
        # Update light brightness step-by-step
        posno = currentposition.split()[0]
        logging.getLogger("HWR").debug("Moving brightness to: %s" % posno)

        self.blight.moveToPosition(posno)

        self.emit("predefinedPositionChanged", (currentposition, 0))

    def is_ready(self):
        state = self.get_state()
        return state == ALBAZoomMotorAutoBrightness.READY


def test():
    from mxcubecore import HardwareRepository as HWR

    hwr = HWR.get_hardware_repository()
    hwr.connect()

    zoom = hwr.get_hardware_object("/zoom-auto-brightness")

    print(type(zoom.get_state()))

    print("     Zoom position is : ", zoom.get_value())
    print("Zoom position name is : ", zoom.get_current_position_name())
    print("               Moving : ", zoom.motorIsMoving())
    print("                State : ", zoom.get_state())
    print("            Positions : ", zoom.get_predefined_positions_list())


if __name__ == "__main__":
    test()

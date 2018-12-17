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
<device class="ALBAZoomMotorAutoBrightness">
  <object role="zoom" hwrid="/zoom"></object>
  <object role="blight" hwrid="/blight"></object>
</device>
"""

from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging
import os
import PyTango

__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAZoomMotorAutoBrightness(BaseHardwareObjects.Device):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor autobrightness IOR")

        self.zoom = self.getObjectByRole('zoom')
        self.blight = self.getObjectByRole('blight')
 
        self.zoom.positionChannel.connectSignal("update", self.positionChanged)
        self.zoom.stateChannel.connectSignal("update", self.stateChanged)

    def getPredefinedPositionsList(self):
        retlist = self.zoom.getPredefinedPositionsList()
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        return retlist

    def moveToPosition(self, posno):
        self.zoom.moveToPosition(posno)
        state = self.zoom.getState()

    def motorIsMoving(self):
        return self.zoom.motorIsMoving()

    def getLimits(self):
        return self.zoom.getLimits()

    def getState(self):
        return self.zoom.getState()
   
    def getPosition(self):
        return self.zoom.getPosition()
   
    def getCurrentPositionName(self):
         return self.zoom.getCurrentPositionName()
    
    def stateChanged(self, state):
        self.emit('stateChanged', (self.getState(), ))

    def positionChanged(self, currentposition):
        currentposition = self.getCurrentPositionName()
        logging.getLogger("HWR").debug("predefinedPositionChanged emitted: %s" % currentposition)
        # Update light brightness step-by-step
        posno = currentposition.split()[0]
        self.blight.moveToPosition(posno)
        
        self.emit('predefinedPositionChanged', (currentposition, 0))

    def isReady(self):
        state = self.getState()
        return state == ALBAZoomMotorAutoBrightness.READY


def test_hwo(hwo):
  print type(hwo.getState() )

  print "     Zoom position is : ",hwo.getPosition()
  print "Zoom position name is : ",hwo.getCurrentPositionName()
  print "               Moving : ",hwo.motorIsMoving()
  print "                State : ",hwo.getState()
  print "            Positions : ",hwo.getPredefinedPositionsList()


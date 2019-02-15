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

The ALBAFastShutter hardware object is a variation of the ALBAEpsActuator
where the command to open/close is done on a different channel than the 
reading of the shutter state.

The interface is otherwise exactly the same as the ALBAEpsActuator

Example XML::

  <device class="ALBAFrontEnd">
    <username>Front Shutter</username>
    <taurusname>bl13/ct/eps-plc-01</taurusname>
    <channel type="sardana" polling="events" name="actuator">fe_open</channel>
    <channel type="sardana" name="open_command">OPEN_FE</channel>
    <channel type="sardana" name="close_command">CLOSE_FE</channel>
    <states>Open,Closed</states>
  </device>

'''

from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging

from ALBAEpsActuator import ALBAEpsActuator

class ALBAFrontEnd(ALBAEpsActuator):

    def init(self):
        ALBAEpsActuator.init(self)

        self.open_channel = self.getChannelObject('open_command')
        self.close_channel = self.getChannelObject('close_command')

    def cmdIn(self):
        self.open_channel.setValue(True)
        # self.actuator_channel.setValue(1)

    def cmdOut(self):
        self.close_channel.setValue(True)
        # self.actuator_channel.setValue(0)

def test_hwo(hwo):
    print "Name is: ",hwo.getUserName()
    print "Shutter state is: ",hwo.getState()
    print "Shutter status is: ",hwo.getStatus()

    #print "Opening it"
    #print hwo.open()
    #print "Closing it"
    #print hwo.close()


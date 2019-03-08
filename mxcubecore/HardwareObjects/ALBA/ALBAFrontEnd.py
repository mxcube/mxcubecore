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
[Name] ALBAFrontEnd

[Description]
The ALBAFastShutter hardware object is a variation of the ALBAEpsActuator
where the command to open/close is done on a different channel than the
reading of the shutter state.

The interface is otherwise exactly the same as the ALBAEpsActuator

[Signals]
- None
"""

from __future__ import print_function

from ALBAEpsActuator import ALBAEpsActuator

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBAFrontEnd(ALBAEpsActuator):
    def __init__(self, name):
        ALBAEpsActuator.__init__(self, name)

        self.chan_open = None
        self.chan_close = None

    def init(self):
        ALBAEpsActuator.init(self)

        self.chan_open = self.getChannelObject('open_command')
        self.chan_close = self.getChannelObject('close_command')

    def cmdIn(self):
        self.chan_open.setValue(True)

    def cmdOut(self):
        self.chan_close.setValue(True)


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.getState())
    print("Shutter status is: ", hwo.getStatus())

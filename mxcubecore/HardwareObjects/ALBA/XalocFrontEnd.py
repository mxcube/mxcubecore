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
[Name] XalocFrontEnd

[Description]
The XalocFastShutter hardware object is a variation of the XalocEpsActuator
where the command to open/close is done on a different channel than the
reading of the shutter state.

The interface is otherwise exactly the same as the XalocEpsActuator

[Signals]
- None
"""

from __future__ import print_function

import logging

from XalocEpsActuator import XalocEpsActuator

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class XalocFrontEnd(XalocEpsActuator):
    def __init__(self, name):
        XalocEpsActuator.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocFrontEnd")
        self.logger.debug("__init__()")
        self.chan_open = None
        self.chan_close = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        XalocEpsActuator.init(self)

        self.chan_open = self.get_channel_object('open_command')
        self.chan_close = self.get_channel_object('close_command')

    def cmd_in(self):
        self.chan_open.set_value(True)

    def cmd_out(self):
        self.chan_close.set_value(True)


def test_hwo(hwo):
    print("Name is: ", hwo.getUserName())
    print("Shutter state is: ", hwo.get_state())
    print("Shutter status is: ", hwo.get_status())

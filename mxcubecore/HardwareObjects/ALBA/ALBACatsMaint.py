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

from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects

from sample_changer.CatsMaint import CatsMaint
import logging

class ALBACatsMaint(CatsMaint):

    def __init__(self, *args):
        CatsMaint.__init__(self, *args)

    def init(self):
        CatsMaint.init(self)

        # load ALBA attributes and commands from XML
        self._chnAtHome = self.getChannelObject("_chnAtHome")
        self.super_abort_cmd = self.getCommandObject("super_abort")

        # channel to ask diffractometer for mounting position
        self.shifts_channel = self.getChannelObject("shifts")

    def _doAbort(self):
        if self.super_abort_cmd is not None:
            self.super_abort_cmd()
        self._cmdAbort()

    def _doResetMemory(self): 
        """
        Reset CATS memory.
        """
        # Check do_PRO6_RAH first
        if self._chnAtHome.getValue() is True:
            CatsMaint._doResetMemory(self)

    def _doReset(self):
        """
        Reset CATS system.
        """
        self._cmdAbort()  
        self._cmdReset()
        self._doResetMemory()

    def _doOperationCommand(self, cmd, pars):
        """
        Send a CATS command
        
        @cmd: command
        @pars: command arguments
        """
        CatsMaint._doOperationCommand(self)

    def _get_shifts(self):
        """
        Get the mounting position from the Diffractometer DS.

        @return: 3-tuple
        """
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.getValue()
        else:
            shifts = None
        return shifts

def test_hwo(hwo):
    print hwo._get_shifts()

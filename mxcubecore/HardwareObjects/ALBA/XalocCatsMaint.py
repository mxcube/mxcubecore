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
[Name] XalocCatsMaint

[Description]
HwObj used to operate the CATS sample changer via Tango in maintenance mode

[Signals]
- None
"""

#from __future__ import print_function
import logging
from mxcubecore.HardwareObjects.CatsMaint import CatsMaint

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocCatsMaint(CatsMaint):

    def __init__(self, *args, **kwargs):
        CatsMaint.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger("HWR.XalocCatsMaint")
        self.chan_shifts = None
        self.chan_at_home = None
        self.cmd_super_abort = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        CatsMaint.init(self)

        # channel to ask diffractometer for mounting position
        self.chan_shifts = self.get_channel_object("shifts")
        self.chan_at_home = self.get_channel_object("_chnAtHome")
        self.cmd_super_abort = self.get_command_object("super_abort")

        # To get acces to recovery functions
        self.Cats90 = self.get_object_by_role("cats90")

    def _do_abort(self):
        if self.cmd_super_abort is not None:
            self.cmd_super_abort()
        self._cmdAbort()

    def _do_reset_memory(self):
        """
        Reset CATS memory.
        """
        # Check do_PRO6_RAH first
        if self.chan_at_home.get_value() is True:
            CatsMaint._do_reset_memory(self)

    def _check_unknown_sample_presence(self):
        self.Cats90._check_unknown_sample_presence()

    def _check_incoherent_sample_info(self):
        """
          Check for sample info in CATS but no physically mounted sample
           (Fix failed PUT)
          Returns False in case of incoherence, True if all is ok
        """
        self.Cats90._check_incoherent_sample_info()

    def _do_recover_failure(self):
        """
          Failed get
        """
        self.Cats90._do_recover_failure()

    def _do_reset(self):
        """
           Reset CATS system after failed put
           Deletes sample info on diff, but should retain info of samples on tools, eg when doing picks
           TODO: tool2 commands are not working, eg SampleNumberInTool2
        """
        self.Cats90._do_reset()

    def _get_shifts(self):
        """
        Get the mounting position from the Diffractometer DS.

        @return: 3-tuple
        """
        if self.chan_shifts is not None:
            shifts = self.chan_shifts.get_value()
        else:
            shifts = None
        return shifts

    def re_emit_signals(self):
        self.emit("runningStateChanged", (self._running,))
        self.emit("powerStateChanged", (self._powered,))
        self.emit("toolStateChanged", (self._toolopen,))
        self.emit("messageChanged", (self._message,))
        self.emit("barcodeChanged", (self._barcode,))
        self.emit("lid1StateChanged", (self._lid1state,))
        self.emit("lid2StateChanged", (self._lid2state,))
        self.emit("lid3StateChanged", (self._lid3state,))
        self.emit("regulationStateChanged", (self._regulating,))



def test_hwo(hwo):
    print(hwo._get_shifts())

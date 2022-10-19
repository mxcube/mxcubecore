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
XalocMiniDiff

[Description]
Specific HwObj for M2D2 diffractometer @ ALBA

[Emitted signals]
- pixelsPerMmChanged
- kappaMotorMoved
- phiMotorMoved
- stateChanged
- zoomMotorPredefinedPositionChanged
- minidiffStateChanged
- minidiffPhaseChanged
"""

import logging
import PyTango

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"
__author__ = "Roeland Boer"

class XalocLN2Shower(HardwareObject):
    """
    Specific liquid nitrogen shower HwObj for XALOC beamline.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.logger = logging.getLogger("HWR.XalocLN2Shower")
        self.userlogger = logging.getLogger("user_level_log")

        self.username = None
        self.chn_operation_mode = None
        self.operation_mode = None
        self.is_pumping_attr = None
        self.cmd_ln2shower_wash = None
        self.cmd_ln2shower_cold = None
        self.cmd_ln2shower_setflow = None
        self.cmd_ln2shower_on = None
        self.cmd_ln2shower_off = None
        self.cmd_ln2shower_sleep = None
 
    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.username = self.get_property("username")
        
        self.chn_operation_mode = self.get_channel_object("operation_mode")
        
        self.cmd_ln2shower_wash = self.get_command_object("ln2shower_wash")
        self.cmd_ln2shower_cold = self.get_command_object("ln2shower_cold")
        self.cmd_ln2shower_setflow = self.get_command_object("ln2shower_setflow")
        self.cmd_ln2shower_on = self.get_command_object("ln2shower_on")
        self.cmd_ln2shower_off = self.get_command_object("ln2shower_off")
        self.cmd_ln2shower_sleep = self.get_command_object("ln2shower_sleep")
        
        self.connect(self.chn_operation_mode, "update", self.operation_mode_changed)
        
    def run_ln2shower_wash(self, washflow = 120):
        #TODO: move diff to transfer phase first, use XalocMiniDiff set_phase method
        
        self.logger.debug( "get_current_phase %s" % HWR.beamline.diffractometer.get_current_phase() ) 
        if HWR.beamline.diffractometer.get_current_phase() != HWR.beamline.diffractometer.PHASE_TRANSFER:
            HWR.beamline.diffractometer.set_phase( HWR.beamline.diffractometer.PHASE_TRANSFER, timeout = 20 )
        if HWR.beamline.diffractometer.get_current_phase() == HWR.beamline.diffractometer.PHASE_TRANSFER:
            self.cmd_ln2shower_wash(washflow, wait = False)
        else:
            return False
        return True
            
    def run_ln2shower_off(self):
        self.cmd_ln2shower_off(wait = False)

    def operation_mode_changed(self, value):
        if self.operation_mode != int( value ):
            self.operation_mode = int( value )
            if self.operation_mode in [3]:
                self.is_pumping_attr = True
            else:
                self.is_pumping_attr = False
            self.emit("ln2showerIsPumpingChanged", self.is_pumping_attr)
 
    def is_pumping(self):
        return self.is_pumping_attr

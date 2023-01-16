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
Liquid nitrogen shower hardware object

[Description]
Specific HwObj for the liquid nitrogen pump installed at XALOC to wash the crystal

[Emitted signals]
- ln2showerIsPumpingChanged
- ln2showerFault

TODO: when the dewar is empty, the operation is INVALID and the State is FAULT
"""

import logging
import PyTango
import time

from taurus.core.tango.enums import DevState

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import Device

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"
__author__ = "Roeland Boer"

class XalocCryostream(Device):
    """
    Specific liquid nitrogen shower HwObj for XALOC beamline.
    """

    def __init__(self, name):
        Device.__init__(self, name)

        self.logger = logging.getLogger("HWR.XalocCryostream")
        self.userlogger = logging.getLogger("user_level_log")

        self.username = None
        self.chn_state = None
        self.chn_gas_temp= None
        self.state = None
        self.gas_temp = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))

        self.username = self.get_property("username")
        self.chn_gas_temp = self.get_channel_object("gas_temp")
        self.chn_state = self.get_channel_object("State")

        self.connect(self.chn_gas_temp, "update", self.gas_temp_changed)
        self.connect(self.chn_state, "update", self.state_changed)

    def state_changed(self, value):
        """
          value can be DevState.FAULT, DevState.ON
        """
        if value is not None:
            if self.state != value:
                self.state = value
                self.emit("stateChanged", (self.state,) )
                if value in [DevState.FAULT]:
                    self.emit("cryostreamFault", (True,) )
                else:
                    self.emit("cryostreamFault", (False,) )

    def gas_temp_changed(self, value):
        if value is not None:
            if self.gas_temp != value:
                self.gas_temp = value
                self.emit("gasTempChanged", (self.gas_temp,) )
        

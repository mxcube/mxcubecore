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
ALBAMachineInfo

[Description]
Hardware Object is used to get relevant machine information
(machine current, time to next injection, status, etc)
Based on EMBL HwObj

[Channels]
- MachineCurrent
- TopUpRemaining
- State

[Commands]

[Emited signals]
- valuesChanged

[Functions]
- None

[Included Hardware Objects]
- None


Example Hardware Object XML file :
==================================
<equipment class="ALBAMachineInfo">
    <username>Mach</username>
    <taurusname>mach/ct/gateway</taurusname>
    <channel type="sardana" name="MachStatus" polling="1000">State</channel>
    <channel type="sardana" name="MachCurrent" polling="1000">Current</channel>
    <channel type="sardana" name="TopUpRemaining" polling="1000">TopUpRemaining</channel>
</equipment>
"""

import logging
import time
from gevent import spawn
from urllib2 import urlopen
from datetime import datetime, timedelta
from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import Equipment


__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAMachineInfo(Equipment):
    """
    Descript. : Displays actual information about the machine status.
    """

    def __init__(self, name):
        Equipment.__init__(self, name)
        self.logger = logging.getLogger("HWR MachineInfo")
        self.logger.info("__init__()")

        """
        Descript. :
        """
        # Parameters values
        self.values_dict = {}
        self.values_dict["mach_current"] = None
        self.values_dict["mach_status"] = ""
        self.values_dict["topup_remaining"] = ""
        # Dictionary for booleans indicating if values are in range
        #        self.values_in_range_dict = {}
        self.chan_mach_current = None
        self.chan_mach_status = None
        self.chan_topup_remaining = None

    def init(self):
        """
        Descript. : Inits channels from xml configuration.
        """
        try:
            self.chan_mach_current = self.get_channel_object("MachCurrent")
            if self.chan_mach_current is not None:
                self.chan_mach_current.connect_signal(
                    "update", self.mach_current_changed
                )

            self.chan_mach_status = self.get_channel_object("MachStatus")
            if self.chan_mach_status is not None:
                self.chan_mach_status.connect_signal("update", self.mach_status_changed)

            self.chan_topup_remaining = self.get_channel_object("TopUpRemaining")
            if self.chan_topup_remaining is not None:
                self.chan_topup_remaining.connect_signal(
                    "update", self.topup_remaining_changed
                )
        except KeyError:
            self.logger.warning("%s: cannot read machine info", self.name())

    def mach_current_changed(self, value):
        """
        Descript. : Function called if the machine current is changed
        Arguments : new machine current (float)
        Return    : -
        """
        if (
            self.values_dict["mach_current"] is None
            or abs(self.values_dict["mach_current"] - value) > 0.10
        ):
            self.values_dict["mach_current"] = value
            self.re_emit_values()
            self.logger.debug("New machine current value=%smA" % value)

    def mach_status_changed(self, status):
        """
        Descript. : Function called if machine status is changed
        Arguments : new machine status (string)
        Return    : -
        """
        self.values_dict["mach_status"] = str(status)
        self.re_emit_values()
        self.logger.debug("New machine status=%s" % status)

    def topup_remaining_changed(self, value):
        """
        Descript. : Function called if topup ramaining is changed
        Arguments : new topup remainin (float)
        Return    : -
        """
        self.values_dict["topup_remaining"] = value
        self.re_emit_values()
        self.logger.debug("New top-up remaining time=%ss" % value)

    def re_emit_values(self):
        """
        Descript. : Updates storage disc information, detects if intensity
                    and storage space is in limits, forms a value list
                    and value in range list, both emited by qt as lists
        Arguments : -
        Return    : -
        """

        values_to_send = []
        values_to_send.append(self.values_dict["mach_current"])
        values_to_send.append(self.values_dict["mach_status"])
        values_to_send.append(self.values_dict["topup_remaining"])

        self.emit("valuesChanged", values_to_send)
        self.logger.debug("SIGNAL valuesChanged emitted")

    def get_mach_current(self):
        try:
            value = self.chan_mach_current.get_value()
        except Exception as e:
            self.logger.error("Cannot read machine current value, returning 0")
            value = 0
        finally:
            return value
            # return self.values_dict['mach_current']

    def get_current(self):
        return self.get_mach_current()

    def get_message(self):
        return "Machinfo status: %s" % self.get_mach_status()

    #    def get_current_value(self):
    #        """
    #        Descript. :
    #        """
    #        return self.values_dict['current']

    def get_mach_status(self):
        return self.chan_mach_status.get_value()

    #        return self.values_dict['mach_status']

    def get_topup_remaining(self):
        return self.chan_topup_remaining.get_value()


#        return self.values_dict['remaining']


def test_hwo(hwo):
    print("Current is", hwo.get_current())

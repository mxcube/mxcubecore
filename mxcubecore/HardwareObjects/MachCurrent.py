# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Machine Current Tango Hardware Object
Example XML:
<object class = "MachCurrent">
  <username>label for users</username>
  <tangoname>orion:10000/fe/id(or d)/xx</tangoname>
  <channel type="tango" name="OperatorMsg" polling="2000">SR_Operator_Mesg</channel>
  <channel type="tango" name="Current" polling="2000">SR_Current</channel>
  <channel type="tango" name="FillingMode" polling="2000">SR_Filling_Mode</channel>
  <channel type="tango" name="RefillCountdown" polling="2000">SR_Refill_Countdown</channel>
</object>
"""

import logging
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)

__copyright__ = """ Copyright © 2010-2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class MachCurrent(AbstractMachineInfo):
    """Tango implementation"""

    def __init__(self, name):
        super().__init__(name)
        self.opmsg = ""

    def init(self):
        try:
            curr = self.get_channel_object("Current")
            curr.connect_signal("update", self.value_changed)
            self.update_state(self.STATES.READY)
        except Exception as err:
            logging.getLogger("HWR").exception(err)

    def value_changed(self, value):
        """Get information from the control software, emit valueChanged"""
        value = value or self.get_current()

        try:
            opmsg = self.get_channel_object("OperatorMsg").get_value()
            fillmode = self.get_channel_object("FillingMode").get_value()
            fillmode = fillmode.strip()

            refill = self.get_channel_object("RefillCountdown").get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(err)
            opmsg, fillmode, value, refill = ("", "", -1, -1)

        if opmsg and opmsg != self.opmsg:
            self.opmsg = opmsg
            logging.getLogger("user_level_log").info(self.opmsg)
        self.emit("valueChanged", (value, opmsg, fillmode, refill))

    def get_current(self) -> float:
        """Read the ring current.
        Returns:
            (float): Ring current [mA]
        """
        try:
            return self.get_channel_object("Current").get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(err)
            return -1

    def get_message(self) -> str:
        try:
            return self.get_channel_object("OperatorMsg").get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(err)
            return ""

    def get_fill_mode(self) -> str:
        try:
            return self.get_channel_object("FillingMode").get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(err)
            return ""

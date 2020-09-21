#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Read the state of the hutch from the PSS device server and take actions
when enter (1) or interlock (0) the hutch.
0 = The hutch has been interlocked and the sample environment should be made
     ready for data collection. The actions are extract the detector cover,
     move the detector to its previous position, set the MD2 to Centring.
1 = The interlock is cleared and the user is entering the hutch to change
      the sample(s). The actions are insert the detector cover, move the
      detecto to a safe position, set MD2 to sample Transfer.
Example xml file:
<object class = "ESRF.BlissHutchTrigger">
  <username>Hutchtrigger</username>
  <pss_tangoname>acs:10000/bl/sa-pss/id30-crate02</pss_tangoname>
  <polling_interval>1</polling_interval>
  <pss_card_ch>9/4</pss_card_ch>
  <object href="/bliss" role="controller"/>
</object>
"""

import logging
from gevent import sleep, spawn
from PyTango.gevent import DeviceProxy
from PyTango import DevFailed
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissHutchTrigger(HardwareObject):
    """Read the state of the hutch from the PSS and take actions."""

    def __init__(self, name):
        super(BlissHutchTrigger, self).__init__(name)
        self.read_only = True
        self._proxy = None
        self.card = None
        self.channel = None
        self._nominal_value = None
        self._poll_task = None
        self.username = None
        self.ctrl_obj = None

    def init(self):
        """Initialise properties and polling"""
        self.username = self.getProperty("username")
        self.ctrl_obj = self.getObjectByRole("controller")
        tangoname = self.getProperty("pss_tangoname")
        try:
            self._proxy = DeviceProxy(tangoname)
        except DevFailed as _traceback:
            last_error = _traceback[-1]
            msg = f"{self.name()}: {last_error['desc']}"
            raise RuntimeError(msg)

        pss = self.getProperty("pss_card_ch")
        try:
            self.card, self.channel = map(int, pss.split("/"))
        except AttributeError:
            msg = f"{self.name()}: cannot find PSS number"
            raise RuntimeError(msg)

        self._nominal_value = self.get_value()
        self._poll_task = spawn(self._do_polling)

    def _do_polling(self):
        while True:
            self.update_value(self.get_value())
            sleep(self.getProperty("polling_interval", 1))

    def get_value(self):
        """Get the interlock value
        Returns:
            (bool): 0 = Hutch interlocked, 1 = Hutch not interlocked.
        """
        _ch1 = self._proxy.GetInterlockState([self.card - 1, 2 * (self.channel - 1)])[0]
        _ch2 = self._proxy.GetInterlockState(
            [self.card - 1, 2 * (self.channel - 1) + 1]
        )[0]
        return _ch1 & _ch2

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
        """
        if value is None:
            value = self.get_value()

        if self._nominal_value != value:
            self._nominal_value = value
            self.emit("valueChanged", (value,))

            self.macro(1 - value)

    def macro(self, entering_hutch, **kwargs):
        """Take action as function of the PSS state
        Args:
            entering_hutch (bool): True if entering (interlock state = 1)
        """
        logging.getLogger("user_level_log").info(
            "%s hutch", "entering" if entering_hutch else "leaving"
        )
        self.ctrl_obj.hutch_actions(entering_hutch, hutch_trigger=True, **kwargs)

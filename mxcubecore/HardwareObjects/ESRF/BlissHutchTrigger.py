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
  <username>Hutch Trigger</username>
  <pss_tango_device>acs:10000/bl/sa-pss/id30-crate02</pss_tango_device>
  <polling_interval>5</polling_interval>
  <pss_card_ch>9/4</pss_card_ch>
  <object href="/bliss" role="controller"/>
  <values>{"ENABLED": 1, "DISABLED": 0}</values>
</object>
"""

import logging
from gevent import sleep, spawn
from PyTango.gevent import DeviceProxy
from PyTango import DevFailed
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissHutchTrigger(AbstractNState):
    """Read the state of the hutch from the PSS and take actions."""

    def __init__(self, name):
        super(BlissHutchTrigger, self).__init__(name)
        self._bliss_obj = None
        self._proxy = None
        self.card = None
        self.channel = None
        self._pss_value = None
        self._nominal_value = None
        self._polling_interval = None
        self._poll_task = None

    def init(self):
        """Initialise properties and polling"""
        super(BlissHutchTrigger, self).init()
        self._bliss_obj = self.get_object_by_role("controller")
        tango_device = self.get_property("pss_tango_device")
        try:
            self._proxy = DeviceProxy(tango_device)
        except DevFailed as _traceback:
            last_error = _traceback[-1]
            msg = f"{self.name()}: {last_error['desc']}"
            raise RuntimeError(msg)

        pss = self.get_property("pss_card_ch")
        try:
            self.card, self.channel = map(int, pss.split("/"))
        except AttributeError:
            msg = f"{self.name()}: cannot find PSS number"
            raise RuntimeError(msg)

        # polling interval [s]
        self._polling_interval = self.get_property("polling_interval", 5)
        self._pss_value = self.get_pss_value()
        # enable by default
        self.update_value(self.VALUES.ENABLED)
        self._poll_task = spawn(self._do_polling)

    def _do_polling(self):
        """Do the polling of the PSS system"""
        while True:
            self._update_value(self.get_pss_value())
            sleep(self._polling_interval)

    def get_value(self):
        """The value corresponds to activate/deactivate the hutch trigger
        polling.
        Returns:
            (ValueEnum): Last set value.
        """
        return self._nominal_value

    def set_value(self, value, timeout=0):
        super(BlissHutchTrigger, self).set_value(value, timeout=0)

    def _set_value(self, value):
        """Set the hutch trigger enable/disable value
        Args:
            value (ValueEnum): ENABLED/DISABLED.
        """
        self._nominal_value = value
        self.emit("valueChanged", (value,))

    def get_pss_value(self):
        """Get the interlock value
        Returns:
            (bool): 0 = Hutch interlocked, 1 = Hutch not interlocked.
        """
        _ch1 = self._proxy.GetInterlockState([self.card - 1, 2 * (self.channel - 1)])[0]
        _ch2 = self._proxy.GetInterlockState(
            [self.card - 1, 2 * (self.channel - 1) + 1]
        )[0]
        return _ch1 & _ch2

    def _update_value(self, value=None):
        """Check if the pss value has changed (door opens/closes).
        Args:
            value (bool): The value
        """
        if self._nominal_value == self.VALUES.ENABLED:
            if value is None:
                value = self.get_pss_value()

            if self._pss_value != value:
                self._pss_value = value
                # now do the action
                self.hutch_actions(1 - value)

    def hutch_actions(self, enter, **kwargs):
        """Take action as function of the PSS state
        Args:
            enter(bool): True if entering hutch (interlock state = 1)
        """
        msg = "%s hutch" % ("Entering" if enter else "Leaving")
        logging.getLogger("user_level_log").info(msg)
        self._bliss_obj.hutch_actions(enter, hutch_trigger=True, **kwargs)

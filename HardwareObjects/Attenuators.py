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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.


import gevent
from HardwareRepository.HardwareObjects.abstract.AbstractAttenuators import (
    AbstractAttenuators
)


class Attenuators(AbstractAttenuators):

    def __init__(self, name):
        AbstractAttenuators.__init__(self, name)

        self.chan_att_value = None
        self.chan_att_state = None
        self.chan_att_limits = None

    def init(self):
        self.chan_att_value = self.getChannelObject("chanAttValue")
        self.chan_att_value.connectSignal("update", self.set_transmission)
        self.chan_att_state = self.getChannelObject("chanAttState")
        self.chan_att_state.connectSignal("update", self.set_state)
        self.chan_att_limits = self.getChannelObject("chanAttLimits")
        self.chan_att_limits.connectSignal("update", self.set_limits)

        self.update_values()

    def set_transmission(self, value, timeout=None):
        if timeout is not None:
            self._state = "busy"
            self.chan_att_value.setValue(value)
            with gevent.Timeout(timeout, Exception("Timeout waiting for state ready")):
                while self._state != "ready":
                    gevent.sleep(0.1)
        else:
            self.chan_att_value.setValue(value)

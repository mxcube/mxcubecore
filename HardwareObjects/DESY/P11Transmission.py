#
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.


import gevent
import logging

from HardwareRepository.HardwareObjects.abstract.AbstractTransmission import (
    AbstractTransmission,
)

log = logging.getLogger("HWR")

class P11Transmission(AbstractTransmission):
    def __init__(self, name):
        super(P11Transmission, self).__init__(name)

        self.chan_read_value = None
        self.chan_set_value = None
        self.chan_state = None

        self._value = None

    def init(self):

        limits = self.getProperty('limits',None)

        try:
            limits = list(map(float,limits.split(',')))
        except BaseException as e:
            log.error("P11Transmission - cannot parse limits: {}".format(str(e)))
            limits = None

        if limits is None:
            log.error("P11Transmission - Cannot read LIMITS from configuration xml file.  Check values")
            return 
        else:
            self.set_limits(limits)

        self.chan_read_value = self.get_channel_object('chanRead')
        self.chan_set_value = self.get_channel_object('chanSet')
        self.chan_state = self.get_channel_object('chanState')

        if self.chan_read_value is not None:
            self.chan_read_value.connectSignal("update", self.value_changed)

        if self.chan_state is not None:
            self.chan_state.connectSignal("update", self.state_changed)

        self.re_emit_values()

    def re_emit_value(self):
        self.state_changed()
        self.value_changed()

    def get_state(self):
        self.state_changed()
        return self._state

    def get_value(self):
        self.value_changed()
        return self._value

    def state_changed(self, state=None):
        if state is None:
            state = self.chan_state.getValue()

        _state = str(state)
        
        if _state == 'ON':
           self._state = self.STATES.READY
        elif _state == 'MOVING':
           self._state = self.STATES.BUSY
        else:
           self._state = self.STATES.FAULT

        self.emit("stateChanged", self._state)

    def value_changed(self, value=None):
        if value is None:
            value = self.chan_read_value.getValue()

        _value = value * 100.0
        if self._value is None or abs(self._value - _value) > 10e-1:
            self._value = _value
            self.emit("valueChanged", self._value)

    def _set_value(self, value):
        value = value / 100.0
        self.chan_set_value.setValue(value)

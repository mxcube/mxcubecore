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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2010 - 2023 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import gevent
import logging
import time

from mxcubecore.HardwareObjects.abstract.AbstractTransmission import (
    AbstractTransmission,
)

log = logging.getLogger("HWR")


class P11Transmission(AbstractTransmission):
    def __init__(self, name):
        super().__init__(name)

        self.chan_read_value = None
        self.chan_set_value = None
        self.chan_state = None

    def init(self):

        limits = self.get_property("limits", None)

        try:
            limits = list(map(float, limits.split(",")))
        except Exception as e:
            log.error("P11Transmission - cannot parse limits: {}".format(str(e)))
            limits = None

        if limits is None:
            log.error(
                "P11Transmission - Cannot read LIMITS from configuration xml file.  Check values"
            )
            return
        else:
            self.set_limits(limits)

        self.chan_read_value = self.get_channel_object("chanRead")
        self.chan_set_value = self.get_channel_object("chanSet")
        self.chan_state = self.get_channel_object("chanState")

        if self.chan_read_value is not None:
            self.chan_read_value.connect_signal("update", self.value_changed)

        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.state_changed)

        self.re_emit_values()

    def re_emit_value(self):
        self.state_changed()
        self.value_changed()

    def get_state(self):
        self.state_changed()
        return self._state

    def get_value(self):
        return self.chan_read_value.get_value() * 100.0

    def state_changed(self, state=None):

        if state is None:
            state = self.chan_state.get_value()

        _str_state = str(state)

        if _str_state == "ON":
            _state = self.STATES.READY
        elif _str_state == "MOVING":
            _state = self.STATES.BUSY
        else:
            _state = self.STATES.FAULT

        self.update_state(_state)

    def value_changed(self, value=None):
        if value is None:
            _value = self.get_value()
        else:
            _value = value * 100.0

        # update only if needed
        if self._nominal_value is None or abs(self._nominal_value - _value) > 10e-1:
            self.update_value(_value)

    def _set_value(self, value):
        value = value / 100.0
        self.chan_set_value.set_value(value)

        print("============== Setting transmission ==================")

        while self.get_state() == "MOVING":
            time.sleep(0.1)
            print("Changing transmission")

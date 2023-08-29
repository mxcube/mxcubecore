# encoding: utf-8
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

from mxcubecore.BaseHardwareObjects import HardwareObject

class ValueStateChannel(HardwareObject):
    
    def __init__(self, name):
        super(ValueStateChannel,self).__init__(name)

    def init(self):

        self.yellow_states = self.green_states = self.red_states = None
        self.yellow_limits = self.red_limits = None

        self.current_value = -1
        self.current_state = "ON"

        self.chan_value = self.get_channel_object("value")
        if self.chan_value is not None:
            self.chan_value.connect_signal("update", self.value_changed)

        self.chan_state = self.get_channel_object("state")
        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.state_changed)

        self.update_delta = self.get_property('delta')

        green_states = self.get_property('ok_states')
        yellow_states = self.get_property('warning_states')
        red_states = self.get_property('alarm_states')

        yellow_limits = self.get_property('warning_limits')
        red_limits = self.get_property('alarm_limits')

        if green_states:
            self.green_states = [ stat.strip().upper() for stat in green_states.split(",")]
        if yellow_states:
            self.yellow_states = [ stat.strip().upper() for stat in yellow_states.split(",")]
        if red_states:
            self.red_states = [ stat.strip().upper() for stat in red_states.split(",")]

        if yellow_limits:
            lims = [ float(lim.strip()) for lim in yellow_limits.split(",")]
            if len(lims) == 2:
                if lims[0] > lims[1]:
                    self.yellow_limits = lims[1],lims[0]
                else:
                    self.yellow_limits = lims
        if red_limits:
            lims = [ float(lim.strip()) for lim in red_limits.split(",")]
            if len(lims) == 2:
                if lims[0] > lims[1]:
                    self.red_limits = lims[1],lims[0]
                else:
                    self.red_limits = lims


    def is_ready(self):
        return self._state == self.STATES.READY

    def state_changed(self, state=None):
        if state is None:
            state = self.chan_state.get_value()

        self._state = str(state).upper()

        self.update_status()

    def value_changed(self, value=None):
        """
        Event called when value has been changed
        :param pos: float
        :return:
        """
        if value is None:
            value = self.chan_value.get_value()

        if value != self.current_value:
            self.current_value = value

            self.emit("valueChanged", (value))
            self.update_status()

    def update_status(self):
        _state = "ON"
        val = self.current_value

        if self.red_limits:
            llim, hlim = self.red_limits
            if  llim > val or hlim < val:
                _state = "ALARM"

        if _state != "ALARM" and self.yellow_limits:
            llim, hlim = self.yellow_limits
            if  llim > val or hlim < val:
                _state = "WARNING"

        if self._red_states and self._state in self._red_states:
            _state = "ALARM"
        elif self._yellow_states and self._state in self._yellow_states:
            _state = (_state == "ALARM" and _state or "WARNING"

        if _state != self.current_state:
            self.current_state = _state
            self.emit("stateChanged", _state)


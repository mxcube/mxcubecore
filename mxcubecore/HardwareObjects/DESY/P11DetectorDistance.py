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

__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "Motor"

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

class P11DetectorDistance(AbstractMotor):

    def __init__(self,name):
        AbstractMotor.__init__(self, name)

        self.interlock_set = None
        self.limits = None

        self.chan_position = None
        self.chan_state = None
        self.chan_min_value = None
        self.chan_max_value = None
        self.chan_interlock_state = None
        self.cmd_stop = None

    def init(self):
        self.chan_state = self.get_channel_object('axisState')
        if self.chan_state is not None:
           self.chan_state.connect_signal("update", self._set_state)
        self._set_state()

        self.chan_position = self.get_channel_object('axisPosition')
        if self.chan_position is not None:
            self.chan_position.connect_signal("update", self.update_value)
        self.update_value()

        self.chan_min_value = self.get_channel_object('axisMinValue')
        self.chan_max_value = self.get_channel_object('axisMaxValue')

        self.chan_interlock_state = self.get_channel_object('interlockState')
        if self.chan_interlock_state is not None:
           self.chan_interlock_state.connect_signal("update", self.interlock_state_changed)
        self.interlock_state_changed()

        self.cmd_stop = self.get_command_object("stopAxis")
        #if self.cmd_stop:
            #self.cmd_stop.connect_signal("connected", self.connected)
            #self.cmd_stop.connect_signal("disconnected", self.disconnected)

    def connectNotify(self, signal):
        """
        :param signal: signal
        :type signal: signal
        """
        if signal == "stateChanged":
            self.update_state()
        elif signal == "limitsChanged":
            self.update_limits()
        elif signal == "valueChanged":
            self.update_value()

    def connected(self):
        """
        Sets ready
        :return:
        """
        self._set_state()
        #self.update_state(self.STATES.READY)

    def disconnected(self):
        """
        Sets not ready
        :return:
        """
        self.update_state(self.STATES.OFF)

    def _set_state(self, state=None):

        if state is None:
            _state = self.chan_state.get_value()
        else:
            _state = state

        _state = str(_state)
        
        if self.interlock_set is None:
            self.update_interlock_state()

        if not self.interlock_set:
            state = self.STATES.FAULT
            self.log.debug("P11 Detector Distance is FAULT because interlock is not set")
        else:
            if _state == 'ON':
                state = self.STATES.READY
            elif _state == 'MOVING':
                state = self.STATES.BUSY
            else:
                state = self.STATES.FAULT
        
        self.update_state(state)
        return state

    def get_value(self):
        return self.chan_position.get_value()

    def update_value(self, value=None):
        """Updates motor position
        """
        if value is None:
            value = self.chan_position.get_value()

        super(P11DetectorDistance, self).update_value(value)

    def _set_value(self, value):
        """
        Main move method
        :param value: float
        :return:
        """
        ##if self.chan_state is not None:
            #self.update_state(self.STATES.BUSY)
            
        self.chan_position.set_value(value)

    def get_limits(self):  
        min_value = self.chan_min_value.get_value()
        max_value = self.chan_max_value.get_value()
        return [min_value, max_value]

    def abort(self):
        """Stops motor movement
        """
        self.cmd_stop()


    def get_motor_mnemonic(self):
        """
        Returns motor mnemonic
        :return:
        """
        return "DetectorDistance"

    def update_interlock_state(self, state=None):
        if self.chan_interlock_state is None:
            return

        if state is None:
            state = self.chan_interlock_state.get_value()
        self.interlock_set = state
        self.log.debug("P11 DetectorDistance / INTERLOCK is %s" % (self.interlock_set and "SET" or "NOT SET") )
  
    def interlock_state_changed(self, state=None):
        self.update_interlock_state(state)   
        self._set_state() 

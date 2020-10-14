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

"""TINEMotor class defines motor in the TINE control system
"""

import logging
import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class TINEMotor(AbstractMotor):
    """TINEMotor class defines motor in the TINE control system
    """

    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.chan_position = None
        self.chan_state = None
        self.chan_limits = None
        self.cmd_set_position = None
        self.cmd_stop_axis = None
        self.cmd_set_online = None

        self.step_limits = None

    def init(self):
        """Connects to all Tine channels and commands"""

        self.chan_limits = self.get_channel_object("axisLimits", optional=True)
        if self.chan_limits is not None:
            self.chan_limits.connect_signal("update", self.update_limits)
            self.update_limits(self.chan_limits.get_value())
        else:
            try:
                if self.get_property("default_limits"):
                    self.update_limits(eval(self.get_property("default_limits")))
            except Exception:
                pass

        self.chan_position = self.get_channel_object("axisPosition")
        if self.chan_position is not None:
            self.chan_position.connect_signal("update", self.update_value())
        self.update_value(self.chan_position.get_value())

        self.chan_state = self.get_channel_object("axisState", optional=True)
        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.update_state)

        self.cmd_set_position = self.get_command_object("setPosition")
        if self.cmd_set_position:
            self.cmd_set_position.connect_signal("connected", self.connected)
            self.cmd_set_position.connect_signal("disconnected", self.disconnected)

        self.cmd_stop_axis = self.get_command_object("stopAxis")
        if self.cmd_stop_axis:
            self.cmd_stop_axis.connect_signal("connected", self.connected)
            self.cmd_stop_axis.connect_signal("disconnected", self.disconnected)

        self.cmd_set_online = self.get_command_object("setOnline")

        # NBNB TODO change config from 'epsilon' to 'tolerance'?
        self._tolerance = self.get_property("epsilon")

        try:
            self.step_limits = eval(self.get_property("stepLimits"))
        except Exception:
            pass

    def connected(self):
        """
        Sets ready
        :return:
        """
        self.update_state(self.STATES.READY)

    def disconnected(self):
        """
        Sets not ready
        :return:
        """
        self.update_state(self.STATES.OFF)

    def connect_notify(self, signal):
        """
        :param signal: signal
        :type signal: signal
        """
        if self.connected():
            if signal == "stateChanged":
                self.update_state()
            elif signal == "limitsChanged":
                self.update_limits()
            elif signal == "valueChanged":
                self.update_value()

    def get_step_limits(self):
        """Returns step limits
        """
        return self.step_limits

    # def get_position(self):
    #    return self.chan_position.get_value()

    def get_value(self):
        return self.chan_position.get_value()

    def get_state(self):
        """Get HardwareObject state"""
        # NNBNB TODO map channel states to all HardwareObject states
        # TODO add treatment of specific_states
        state = self.chan_state.get_value()
        if type(state) in (tuple, list):
            state = state[0]
        if state in ("ready", 0):
            state = self.STATES.READY
        else:
            state = self.STATES.BUSY
        #
        return state

    def abort(self):
        """Stops motor movement
        """
        self.cmd_stop_axis()

    def _set_value(self, value):
        """
        Main move method
        :param value: float
        :return:
        """
        if self.chan_state is not None:
            self.update_state(self.STATES.BUSY)
            self.chan_state.set_old_value("moving")
        self.cmd_set_position(value)

    def update_value(self, value=None):
        """Updates motor position
        """
        if type(value) in (list, tuple):
            value = value[0]
        super(TINEMotor, self).update_value(value)

    def get_motor_mnemonic(self):
        """
        Returns motor mnemonic
        :return:
        """
        return "TINEMotor"

    def enable_motor(self):
        """
        Enables motor
        """
        if self.cmd_set_online:
            self.cmd_set_online(1)
            gevent.sleep(2)

    def disable_motor(self):
        """
        Disables motor
        """
        if self.cmd_set_online:
            self.cmd_set_online(0)
            gevent.sleep(2)

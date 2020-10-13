#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
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
TangoMotor class defines motor in the Tango control system (used and tested in DESY/P11
"""

from HardwareRepository.utils.mxcube_logging import log
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import AbstractMotor

import gevent

__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "Motor"

class TangoMotor(AbstractMotor):
    """TINEMotor class defines motor in the TINE control system
    """

    default_polling = 500

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
        self.polling = self.getProperty("polling", TangoMotor.default_polling)
        self.actuator_name = self.getProperty("actuator_name", self.name())
        self._tolerance = self.getProperty("tolerance", None)

        self.chan_position = self.get_channel_object("axisPosition", optional=True)
        if self.chan_position is None:
             self.chan_position = self.add_channel(
                  {
                      "type": "tango",
                      "name": "axisPosition",
                      "tangoname": self.tangoname,
                      "polling": self.polling,
                  }, "Position",)

        if self.chan_position is not None:
            self.chan_position.connectSignal("update", self.update_value)
            self.update_value(self.chan_position.getValue())

        self.chan_state = self.get_channel_object("axisState", None)
        if self.chan_state is None:
             self.chan_state = self.add_channel(
                  {
                      "type": "tango",
                      "name": "axisState",
                      "tangoname": self.tangoname,
                      "polling": self.polling,
                  }, "State",)

        if self.chan_state is not None:
            self.chan_state.connectSignal("update", self.motor_state_changed)

        self.chan_limits = self.get_channel_object("axisLimits", optional=True)
        if self.chan_limits is not None:
            self.chan_limits.connectSignal("update", self.update_limits)
            self.update_limits(self.chan_limits.getValue())
        else:
            try:
                if self.getProperty("default_limits"):
                    self.update_limits(eval(self.getProperty("default_limits")))
            except Exception:
                pass

        self.cmd_stop = self.get_command_object("stopAxis")
        if self.cmd_stop is None:
             self.cmd_stop = self.add_command(
                  {
                      "type": "tango",
                      "name": "stopAxis",
                      "tangoname": self.tangoname,
                      "polling": self.polling,
                  }, "Stop",)

    def connectNotify(self, signal):
        """
        :param signal: signal
        :type signal: signal
        """
        if signal == "stateChanged":
            self.motor_state_changed()
        elif signal == "limitsChanged":
            self.update_limits()
        elif signal == "valueChanged":
            self.update_value()

    def get_value(self):
        value = self.chan_position.getValue()
        return value

    def motstate_to_state(self, motstate):

        motstate = str(motstate)
    
        if motstate == "ON":
            state = self.STATES.READY
        elif motstate == "MOVING":
            state = self.STATES.BUSY
        elif motstate == "FAULT":
            state = self.STATES.FAULT
        elif motstate == "OFF":
            state = self.STATES.OFF
        else:
            state = self.STATES.UNKNOWN

        return state

    def motor_state_changed(self, state=None):
        if state == None:
            state = self.chan_state.getValue()

        self.update_state( self.motstate_to_state(state) )

    def abort(self):
        """Stops motor movement
        """
        self.cmd_stop()

    def _set_value(self, value):
        """
        Main move method
        :param value: float
        :return:
        """
        log.debug("TangoMotor.py - Moving motor %s to %s" % (self.name(), value))
        self.start_moving()
        self.chan_position.setValue(value)

    def start_moving(self):
        self.motor_state_changed("MOVING")

        # ensure that the state is updated at least once after the polling time
        # in case we miss the state update
        gevent.spawn(self._update_state)

    def _update_state(self):
        gevent.sleep(0.5)
        self.motor_state_changed(self.chan_state.getValue())
            
    def update_value(self, value=None):
        """Updates motor position
        """
        if value is None:
            value = self.get_value()
        super(TangoMotor, self).update_value(value)

    def get_motor_mnemonic(self):
        """
        Returns motor mnemonic
        :return:
        """
        return "TangoMotor"

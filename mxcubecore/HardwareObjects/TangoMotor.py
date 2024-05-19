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

import gevent

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__credits__ = ["DESY P11"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class TangoMotor(AbstractMotor):
    """TangoMotor class defines motor in the Tango control system"""

    default_polling = 500

    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.chan_position = None
        self.chan_state = None
        self.chan_limits = None
        self.cmd_set_position = None
        self.cmd_stop_axis = None
        self.cmd_set_online = None
        self.latest_position = None
        self.auto_on = False
        self.cmd_on = None
        self.cmd_calibrate = None

        self.step_limits = None

    def init(self):
        """Connects to all Tango channels and commands"""
        self.polling = self.get_property("polling", TangoMotor.default_polling)
        self.actuator_name = self.get_property("actuator_name", self.name())
        self._tolerance = self.get_property("tolerance", 1e-3)

        self.is_simulation = self.get_property("simulation",False)
        self.auto_on = self.get_property("auto_on",False)
        if self.auto_on:
            self.log.debug("AUTO_ON is set for motor %s" % self.name())

        if self.is_simulation:
            self.simulated_pos = 0.0
            self.set_ready()
            return

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
            self.chan_position.connect_signal("update", self.update_value)
            self.update_value(self.chan_position.get_value())

        self.chan_state = self.get_channel_object("axisState", None)
        if self.chan_state is None:
            self.chan_state = self.add_channel(
                {
                    "type": "tango",
                    "name": "axisState",
                    "tangoname": self.tangoname,
                    "polling": self.polling,
                },
                "State",
            )

        if self.chan_state is not None:
            self.chan_state.connect_signal("update", self.motor_state_changed)

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

        self.cmd_stop = self.get_command_object("stopAxis")
        if self.cmd_stop is None:
             self.cmd_stop = self.add_command(
                  {
                      "type": "tango",
                      "name": "stopAxis",
                      "tangoname": self.tangoname,
                  }, "Stop",)

        self.cmd_on = self.get_command_object("onCmd")
        if self.cmd_on is None:
             self.cmd_on = self.add_command(
                  {
                      "type": "tango",
                      "name": "onCmd",
                      "tangoname": self.tangoname,
                  }, "On",)


        self.chan_velocity = self.get_channel_object("velocity", optional=True)

        self.cmd_calibrate = self.get_command_object("calibrate")

        # update values
        self.motor_state_changed()
        self.update_value()

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
        if self.is_simulation:
             return self.simulated_pos
        value = self.chan_position.get_value()
        return value

    def get_velocity(self):
        if self.chan_velocity is not None:
            return self.chan_velocity.get_value()

    def set_velocity(self, value):
        if self.chan_velocity is not None:
            self.chan_velocity.set_value(value)

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
        if state is None:
            state = self.chan_state.get_value()

        self.update_state(self.motstate_to_state(state))

    def set_ready(self):
        self.update_state(self.STATES.READY)

    def is_moving(self):
        return ( (self.get_state() == self.STATES.BUSY ) or (self.get_state() == self.SPECIFIC_STATES.MOVING))

    def abort(self):
        """Stops motor movement"""
        self.cmd_stop()

    def calibrate(self, value):
        self.cmd_calibrate(value)

    def _set_value(self, value):
        """
        Main move method
        :param value: float
        :return:
        """
        self.log.debug("TangoMotor.py - Moving motor %s to %s" % (self.id, value))
        if self.is_simulation:
             self.simulated_pos = value
        else:
             self.start_moving()
             self.chan_position.set_value(value)

    def start_moving(self):
        self.motor_state_changed("MOVING")

        if self.auto_on:
            state = str(self.chan_state.get_value())
            if state == "OFF":
                self.cmd_on()
        # ensure that the state is updated at least once after the polling time
        # in case we miss the state update
        gevent.spawn(self._update_state)

    def _update_state(self):
        gevent.sleep(0.5)
        motor_state = self.chan_state.get_value()
        self.log.debug(" reading motor state for %s is %s" % (self.id, str(motor_state)))
        self.motor_state_changed(motor_state)

    def update_value(self, value=None):
        """Updates motor position"""
        if value is None:
            value = self.get_value()
        self.latest_value = value
        super(TangoMotor, self).update_value(value)

    def get_motor_mnemonic(self):
        """
        Returns motor mnemonic
        :return:
        """
        return "TangoMotor"

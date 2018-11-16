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

import logging
import gevent

from AbstractMotor import AbstractMotor

__credits__ = ["EMBL Hamburg"]
__version__ = "2.3"
__category__ = "Motor"


class TINEMotor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.previous_position = None

        self.chan_position = None
        self.chan_state = None
        self.chan_limits = None
        self.cmd_set_position = None
        self.cmd_stop_axis = None
        self.cmd_set_online = None

        self.epsilon = None
        self.username = None
        self.step_limits = None

    def init(self):

        self.chan_limits = self.getChannelObject("axisLimits", optional=True)
        if self.chan_limits is not None:
            self.chan_limits.connectSignal("update", self.motor_limits_changed)
            self.motor_limits_changed(self.chan_limits.getValue())
        else:
            try:
                if self.getProperty("default_limits"):
                    self.motor_limits_changed(eval(self.getProperty("default_limits")))
            except:
                pass

        self.chan_position = self.getChannelObject("axisPosition")
        if self.chan_position is not None:
            self.chan_position.connectSignal("update", self.motor_position_changed)
        self.motor_position_changed(self.chan_position.getValue())

        self.chan_state = self.getChannelObject("axisState", optional=True)
        if self.chan_state is not None:
            self.chan_state.connectSignal("update", self.motor_state_changed)

        self.cmd_set_position = self.getCommandObject("setPosition")
        if self.cmd_set_position:
            self.cmd_set_position.connectSignal("connected", self.connected)
            self.cmd_set_position.connectSignal("disconnected", self.disconnected)

        self.cmd_stop_axis = self.getCommandObject("stopAxis")
        if self.cmd_stop_axis:
            self.cmd_stop_axis.connectSignal("connected", self.connected)
            self.cmd_stop_axis.connectSignal("disconnected", self.disconnected)

        self.cmd_set_online = self.getCommandObject("setOnline")

        self.epsilon = self.getProperty("epsilon")

        self.username = self.getProperty("username")

        try:
            self.step_limits = eval(self.getProperty("stepLimits"))
        except:
            pass

    def connected(self):
        """
        Descript. :
        """
        self.set_ready(True)

    def disconnected(self):
        """
        Descript. :
        """
        self.set_ready(True)

    def connectNotify(self, signal):
        """
        :param signal: signal
        :type signal: signal
        """
        if self.connected():
            if signal == "stateChanged":
                self.motor_state_changed()
            elif signal == "limitsChanged":
                self.motor_limits_changed(self.getLimits())
            elif signal == "positionChanged":
                self.motor_position_changed(self.getPosition())

    def motor_limits_changed(self, limits):
        """Updates motor limits

        :param limits: limits
        :type limits: list of two floats
        """
        self.set_limits(limits)
        self.emit("limitsChanged", (limits,))

    def get_step_limits(self):
        """Returns step limits
        """
        return self.step_limits

    def stop(self):
        """Stops motor movement
        """
        self.cmd_stop_axis()

    def move(self, target, wait=None, timeout=None):
        """
        Descript. :
        """
        if self.chan_state is not None:
            self.set_state(self.motor_states.MOVING)
            self.chan_state.setOldValue("moving")
        if target == float("nan"):

            logging.getLogger().debug(
                "Refusing to move %s to target nan" % self.objName
            )
        else:
            self.cmd_set_position(target)

        if timeout:
            gevent.sleep(2)
            self.wait_ready(timeout)
            self.wait_ready(10)

    def motor_state_changed(self, state):
        """Updates motor state
        """
        if type(state) in (tuple, list):
            state = state[0]

        if state in ("ready", 0):
            self.set_state(self.motor_states.READY)
        else:
            self.set_state(self.motor_states.MOVING)

    def motor_position_changed(self, position):
        """Updates motor position
        """
        if type(position) in (list, tuple):
            position = position[0]
        if (
            self.epsilon is None
            or self.previous_position is None
            or (abs(position - self.previous_position) > self.epsilon)
        ):
            self.set_position(position)
            self.emit("positionChanged", (position,))
            self.previous_position = position

    def getMotorMnemonic(self):
        """
        Descript. :
        """
        return "TINEMotor"

    def wait_ready(self, timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self.is_ready():
                gevent.sleep(0.05)

    def enable_motor(self):
        if self.cmd_set_online:
            self.cmd_set_online(1)
            gevent.sleep(2)

    def disable_motor(self):
        if self.cmd_set_online:
            self.cmd_set_online(0)
            gevent.sleep(2)

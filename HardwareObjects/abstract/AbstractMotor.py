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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Abstract Motor API. Motor states definition"""

import abc
from enum import IntEnum, unique
from gevent import Timeout
from gevent.event import Event
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class MotorStates(IntEnum):
    """Motor states definitions."""

    UNKNOWN = 0
    WARNING = 1
    BUSY = 2
    READY = 3
    FAULT = 4
    HOME = 5
    LIMPOS = 6
    LIMNEG = 7


class AbstractMotor(HardwareObject):
    """Abstract motor API"""

    __metaclass__ = abc.ABCMeta
    READY_STATES = (
        MotorStates.READY,
        MotorStates.LIMPOS,
        MotorStates.LIMNEG,
        MotorStates.HOME,
    )
    unit = None

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._state = MotorStates.UNKNOWN
        self._nominal_value = None
        self._limits = (None, None)
        self._velocity = None
        self._tolerance = None
        self.motor_name = None
        self.username = None
        self._ready_event = None

    def init(self):
        """Initialise some parametrs."""
        self.motor_name = self.getProperty("motor_name")
        self.username = self.getProperty("username") or self.motor_name
        self._tolerance = self.getProperty("tolerance") or 1e-3
        self._ready_event = Event()

    def is_ready(self):
        """Check if the motor state is READY.
        Returns:
            (bool): True if ready, otherwise False.
        """
        return self._ready_event.is_set()

    @abc.abstractmethod
    def get_state(self):
        """Get the motor state
        Returns:
            (enum 'MotorStates'): Motor state.
        """
        return None

    @abc.abstractmethod
    def get_value(self):
        """Read the motor position.
        Returns:
            float: Motor position.
        """
        return None

    def get_limits(self):
        """Return motor low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        return self._limits

    def set_limits(self, limits):
        """Set motor low and high limits.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        self._limits = limits
        self.emit("limitsChanged", (self._limits,))

    def get_velocity(self):
        """Read motor velocity.
        Returns:
            (float): velocity [unit/s]
        """
        return self._velocity

    def set_velocity(self, velocity):
        """Set the motor velocity
        Args:
            velocity (float): target velocity
        """
        self._velocity = velocity

    @abc.abstractmethod
    def _set_value(self, value, wait=True, timeout=None):
        """Move motor to absolute position. Wait the move to finish.
        Args:
            value (float): target value
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """

    def set_value(self, value, wait=True, timeout=None):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target value
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        self._set_value(value)
        self.update_value()

        if wait:
            self.wait_ready(timeout)

    def set_value_relative(self, relative_value, wait=False, timeout=None):
        """Move to value relative to the current. Wait the move to finish.
        Args:
            relative_value (float): relative target value.
            wait (bool): optional - wait until motor movement finished.
            timeout (float): optional - timeout [s].
        """
        self.move(self.get_value() + relative_value, wait, timeout)

    def wait_ready(self, timeout=None):
        """Wait until event ready
        Args:
            (float): timeout [s]
        Raises:
            RuntimeError: Timeout waiting for status ready.
        """
        with Timeout(timeout, RuntimeError("Timeout waiting for status ready")):
            self._ready_event.wait(timeout=timeout)

    def abort(self):
        """Abort the motor movement immediately."""
        raise NotImplementedError

    def stop(self):
        """Stop the motor movement"""
        raise NotImplementedError

    def home(self, timeout=None):
        """Homing procedure.
        Args:
            timeout (float): Timeout [s].
        """
        raise NotImplementedError

    def update_value(self, value=None):
        """Check if the value has changed. Emist signal valueChanged.
        Args:
            value (float): value
        """
        if self._nominal_value is None:
            self._nominal_value = self.get_value()

        if value is None:
            value = self.get_value()

        if abs(value - self._nominal_value) <= self._tolerance:
            return

        self._nominal_value = value
        self.emit("valueChanged", (self._nominal_value,))

    def update_state(self, state=None):
        """Check if the state has changed. Emist signal stateChanged.
        Args:
            state (enum 'MotorState'): state
        """
        if state != self._state:
            if state is None:
                state = self.get_state()
            if state in self.READY_STATES:
                self._ready_event.set()
            else:
                self._ready_event.clear()

            self._state = state
            self.emit("stateChanged", (self._state,))

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emist signal limitsChanged.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        if limits is None:
            limits = self.get_limits()

        if all(limits):
            self._limits = limits
            self.emit("limitsChanged", (self._limits,))

    def update_values(self):
        """ Reemits all signals
        """
        self.update_value()
        self.update_state()
        self.update_limits()

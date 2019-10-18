#! /usr/bin/env python
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Standard abstract HardwareObject with a'value' (e.g. motor, transmission, ...)
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import logging
from abc import ABCMeta, abstractmethod
import gevent.event

from HardwareRepository.BaseHardwareObjects import HardwareObject, HardwareObjectNode

# We should make a standard set of states and use that wherever possible
from somewhere import GeneralState

__credits__ = [" Copyright © 2019 by MXCuBE collaboration. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "20190607"


class AbstractActuator(HardwareObject, HardwareObjectNode):
    """Abstract base class for Abstract actuators"""

    # NB we should separate HardwareObjectNode and HardwareObject for future refactoring

    __metaclass__ = ABCMeta

    # Stete enumeration
    STATE = GeneralState

    # Tuple of states that count as ready
    READY_STATES = (STATE.READY,)

    # Default lower, upper limits
    # Limit handling can be overridden in subclasses
    _limits = (None, None)

    def __init__(self, name):
        super(AbstractActuator, self).__init__(name)

        # event to handle waiting for object to be ready
        self._ready_event = None
        self._state = self.STATE.NOTINITIALIZED

        # Tolerance to discriminate values as being different
        self.value_resolution = None

    def init(self):
        super(AbstractActuator, self).init()
        self._ready_event = gevent.event.Event()

    @abstractmethod
    def get_value(self):
        """Get current value

        Returns:
            Optional[float]
        """
        return None

    @abstractmethod
    def _set_value(self, value):
        """Internal value setter, called by set_value

        Must ensure stateChanged sand valueChanged signals are sent as appropriate

        Asynchronous, should return without waiting for object to be ready

        Must cope sensibly with value None

        Args:
            value (Optional[float]): new value to set

        Returns:

        """
        pass

    def set_value(self, value, timeout=None):
        """Set value, checking for minimum change and timeout

        Args:
            value (float): New value for object
            timeout (Optional[float]): If set waits up to timeout seconds before return

        Returns:

        """

        if not self.is_valid_value(value):
            raise ValueError("Invalid value %s" % value)
        tol = self.value_resolution
        if tol is not None and value is not None:
            current_value = self.get_value()
            if current_value is not None and abs(current_value - value) < tol:
                return
        if timeout:
            if not isinstance(timeout, (int, float)):
                raise TypeError("Invalid data type for timeout: %s" % timeout)
            elif timeout < 0:
                raise ValueError("Negative value for timeout: %s" % timeout)
        self._set_value(value)
        self.wait_ready(timeout)

    def set_value_relative(self, increment, timeout=None):
        """Sets value relative to current value.

        If timeout is set, waits up to timeout for completion.

        Args:
            increment (float): increment to value
            timeout (Optional[float]):  non-negative timeout in seconds

        Returns:

        """
        current_value = self.get_value()
        if current_value is None:
            raise ValueError("Cannot increment %s value None" % self.__class__.__name__)
        self.set_value(current_value + increment, timeout)

    def is_valid_value(self, value):
        """

        Args:
            value (Optional[float]): Value to validate

        Returns:
            bool
        """
        if value is not None:
            lower, upper = self.get_limits()
            if (lower is not None and value < lower) or (
                upper is not None and value > upper
            ):
                logging.getLogger("HWR").warning(
                    "%s value %s not in range %s to %s",
                    self.__class__.__name__,
                    value,
                    lower,
                    upper,
                )
                return False
        return True

    def get_state(self):
        """Get object state

        Returns:
            STATE
        """
        return self._state

    def set_state(self, state):
        """Set objetc state and is_ready.

        Any operation (channel, ...) that changes state must call this function
        as appropriate

        Args:
            state (STATE): new state

        Returns:

        """
        previous_state = self._state
        self._state = state
        if state != previous_state:
            self.emit("stateChanged", state)
            if state in self.READY_STATES:
                self._ready_event.set()
            else:
                self._ready_event.clear()

    def get_limits(self):
        """Optional value limits

        NB the abstract class will always return limit (None, None)

        Returns:
            Tuple[Optional[float],Optional[float]]
        """
        return self._limits

    def set_limits(self, limits):
        """ Set limits. Input is as pair of limits, lowerbound, upperbound
        either of which may be None.

        NB set_limits will raise an error unless a _set_limits function is implemented

        Args:
            limits Tuple[Optional[float], Optional[float]]:

        Returns:
            None
        """
        self._set_limits(limits)
        self.emit("limitsChanged", (limits,)

    def _set_limits(self, limits):
        """ Actual limit-setting function. Raises NotImplementedError unless overwritten
        Args:
            limits Tuple[Optional[float], Optional[float]]:

        Returns:
            None
        """
        raise NotImplementedError(
            "Limis setting not implemented for class %s"
            % self.__class__.__name__
        )

    def is_ready(self):
        """
        Is HardwareObject ready?
        :return: bool
        """
        return self._ready_event.is_set()

    def wait_ready(self, timeout=None):
        """

        :param timeout: Optional[float] timeout in seconds. If None wait forever
        :return:
        """
        if timeout or timeout is None:
            # NB if timeout is 0 do not wait
            success = self._ready_event.wait(timeout=timeout)
            if not success:
                raise RuntimeError("Timeout waiting for status ready")

    def update_values(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("limitsChanged", (self.get_limits(),))
        self.emit("valueChanged", (self.get_value(),))
        self.emit("stateChanged", (self.get_state(),))

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

from abc import ABCMeta, abstractproperty
import gevent.event
from HardwareRepository.BaseHardwareObjects import HardwareObject

# We should make a standard set of states and use that wherever possible
from somewhere import GeneralState

__credits__ = [" Copyright © 2019 by MXCuBE collaboration. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "20190607"


class StandardHardwareObject(HardwareObject):
    """Abstract base class for standard hardware objects"""

    __metaclass__ = ABCMeta

    STATE = GeneralState

    # Default lower, upper limits
    # Limit handling can be overridden in subclasses
    _limits = (None, None)

    def __init__(self, name):
        super(StandardHardwareObject, self).__init__(name)

        # event to handle waiting for object to be ready
        self._ready_event = None
        self._state = self.STATE.NOTINITIALIZED

        # Tolerance to discriminate values as being different
        self.value_resolution = None

    def init(self):
        super(StandardHardwareObject, self).init()
        self.ready_event = gevent.event.Event()

    def accept_new_value(self, value):
        """
        Check if value should be (re)set.
        :param value: Optional[float]
        returns False if value is within tolerance of current value.
        raises ValueError if value outside limits
        :return: bool
        """
        if value is not None:
            lower, upper = self.get_limits()
            tol = self.value_resolution
            if (lower is not None and value < lower) or (
                upper is not None and value > upper
            ):
                raise ValueError(
                    "Value %s not in range %s to %s" % (value, lower, upper)
                )
            elif tol is not None and abs(value - self.value) < tol:
                return False
        return True

    @abstractproperty
    def value(self):
        """
        current value (float or None) of object.
        :return: Optional[float]
        """
        return None

    @value.setter
    def value(self, value):
        pass

    @property
    def state(self):
        """
        Returns current object state
        :return: STATE
        """
        return self._state

    @state.setter
    def state(self, state):
        previous_state = self._state
        self._state = state
        if state != previous_state:
            self.emit("stateChanged", state)
            if state == self.STATE.READY:
                self._ready_event.set()
            elif previous_state == self.STATE.READY:
                self._ready_event.clear()

    @property
    def limits(self):
        """
        Returns value limits as a tuple of (lower_limit, upper_limit)

        NB the abstract class will always return limit (None, None)
        Subclasses should implement their own read_only limit property
        and their own mechanism for setting and modifying limits
        :return: Tuple[Optional[float], Optional[float]]
        """
        return self._limits

    def is_ready(self):
        """
        Is HardwareObject ready?
        :return: bool
        """
        return self._ready_event.is_set()

    def wait_ready(self, timeout=None):
        """

        :param timeout: flost timeout in seconds
        :return:
        """
        success = self._ready_event.wait(timeout=timeout)
        if not success:
            raise RuntimeError("Timeout waiting for status ready")

    def set_value_to(self, value, timeout):
        """
        Sets value and waits for completion.
        NB actual value set may differ from input value

        :param value: float (0 - 100)
        :param timeout: float
        :return:
        """
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Invalid value for timeout: %s" % timeout)
        self.value = value
        self.wait_ready(timeout)

    def update_values(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("limitsChanged", (self.limits,))
        self.emit("valueChanged", (self.value,))
        self.emit("stateChanged", (self.state,))

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

"""Abstract Actuator class.
Defines the set/update value, get/set/update limits and validate_value
methods and the get_value and_set_value abstract methods.
Initialises the actuator_name, username, read_only and default_value properties.
Emits signals valueChanged and limitsChanged.
"""

import abc
import math
from ast import literal_eval
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractActuator(HardwareObject):
    """Abstract actuator"""

    __metaclass__ = abc.ABCMeta

    unit = None

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._nominal_value = None
        self._nominal_limits = (None, None)
        self.actuator_name = None
        self.read_only = False
        self.default_value = None
        self.username = None

    def init(self):
        """Initialise actuator_name, username, read_only and default_value
        properties.
        """
        self.actuator_name = self.getProperty("actuator_name")
        self.read_only = self.getProperty("read_only") or False
        self.default_value = self.getProperty("default_value")
        if self.default_value is not None:
            self.update_value(self.default_value)
        limits = self.getProperty("default_limits")
        if limits:
            try:
                self._nominal_limits = tuple(literal_eval(limits))
            except TypeError:
                print("Invalid limits")
        self.username = self.getProperty("username")

    @abc.abstractmethod
    def get_value(self):
        """Read the actuator position.
        Returns:
            value: Actuator position.
        """
        return None

    def get_limits(self):
        """Return actuator low and high limits.
        Returns:
            (tuple): two elements (low limit, high limit) tuple.
        """
        return self._nominal_limits

    def set_limits(self, limits):
        """Set actuator low and high limits. Emits signal limitsChanged.
        Args:
            limits (tuple): two elements (low limit, high limit) tuple.
        Raises:
            ValueError: Attempt to set limits for read-only Actuator.
        """
        if self.read_only:
            raise ValueError("Attempt to set limits for read-only Actuator")

        self._nominal_limits = limits
        self.emit("limitsChanged", (self._nominal_limits,))

    def validate_value(self, value):
        """Check if the value is within limits.
        Args:
            value: value
        Returns:
            (bool): True if within the limits
        """
        return True

    @abc.abstractmethod
    def _set_value(self, value):
        """Implementation of specific set actuator logic.
        Args:
            value: target value
        """

    def set_value(self, value, timeout=0):
        """ Set actuator to value.
        Args:
            value: target value
            timeout (float): optional - timeout [s],
                             If timeout == 0: return at once and do not wait
                                              (default);
                             if timeout is None: wait forever.
        Raises:
            ValueError: Invalid value or attemp to set read only actuator.
            RuntimeError: Timeout waiting for status ready  # From wait_ready
        """
        if self.read_only:
            raise ValueError("Attempt to set value for read-only Actuator")
        if self.validate_value(value):
            self.update_state(self.STATES.BUSY)
            self._set_value(value)
            self.update_value()
            if timeout == 0:
                return
            self.wait_ready(timeout)
        else:
            raise ValueError("Invalid value %s" % str(value))

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value: value
        """
        if value is None:
            value = self.get_value()

        if self._nominal_value != value:

            self._nominal_value = value
            self.emit("valueChanged", (value,))

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emits signal limitsChanged.
        Args:
            limits (tuple): two elements tuple (low limit, high limit).
        """
        if not limits:
            limits = self.get_limits()

        if self._nominal_limits != limits:
            # All values are not NaN
            if not any(isinstance(lim, float) and math.isnan(lim) for lim in limits):
                self._nominal_limits = limits
                self.emit("limitsChanged", (limits,))

    def re_emit_values(self):
        """Update values for all internal attributes"""
        self.update_value(self.get_value())
        self.update_limits(self.get_limits())
        super(AbstractActuator, self).re_emit_values()

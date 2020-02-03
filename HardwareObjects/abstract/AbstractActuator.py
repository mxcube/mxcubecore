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

"""Abstract Actuator"""

import abc
from HardwareRepository.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractActuator(HardwareObject):
    """Abstract actuator"""

    __metaclass__ = abc.ABCMeta

    unit = None

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._nominal_value = None
        self._limits = (None, None)
        self.actuator_name = None
        self.read_only = False
        self.default_value = None

    def init(self):
        """Initialise some parameters."""
        self.actuator_name = self.getProperty("actuator_name")
        self.read_only = self.getProperty("read_only") or False
        self.default_value = self.getProperty("default_value")

    @abc.abstractmethod
    def get_value(self):
        """Read the actuator position.
        Returns:
            float: Actuator position.
        """
        return None

    def get_limits(self):
        """Return actuator low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        return self._limits

    def set_limits(self, limits):
        """Set actuator low and high limits.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        self._limits = limits
        self.emit("limitsChanged", (self._limits,))

    @abc.abstractmethod
    def _set_value(self, value, wait=True, timeout=None):
        """Move actuator to absolute position. Wait the move to finish.
        Args:
            value (float): target value
            wait (bool): optional - wait until actuator movement finished.
            timeout (float): optional - timeout [s].
        """

    def set_value(self, value, wait=True, timeout=None):
        """Move actuator to absolute value. Wait the move to finish.
        Args:
            value (float): target value
            wait (bool): optional - wait until actuator movement finished.
            timeout (float): optional - timeout [s].
        """
        self._set_value(value)
        self.update_value()

        if wait:
            self.wait_ready(timeout)

    def update_value(self, value=None):
        """Check if the value has changed. Emits signal valueChanged.
        Args:
            value (float): value
        """
        if value is None or self._nominal_value is None:
            value = self.get_value()

        self._nominal_value = value
        self.emit("valueChanged", (self._nominal_value,))

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emits signal limitsChanged.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        if limits is None:
            limits = self.get_limits()

        if all(limits):
            self._limits = limits
            self.emit("limitsChanged", (self._limits,))

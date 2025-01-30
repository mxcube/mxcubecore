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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Abstract Actuator."""

from __future__ import annotations

import abc
import math
from ast import literal_eval

from gevent.lock import RLock

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractActuator(HardwareObject):
    """Abstract actuator defines methods common to all moving devices.

    The ``_set_value`` method is the only abtract method that needs to be overloaded
    in each implementation.

    Attributes:
        _nominal_value (float | None):
            Current actuator value.
        default_value (float | None):
            Value specified by XML property, otherwise ``None``.
        _nominal_limits (tuple[float | None, float | None]):
            Values specified by XML property, otherwise ``None``.
        actuator_name (str | None):
            Actuator name specified by XML property, otherwise ``None``.
        read_only (bool):
            Read-only flag specified by XML property, otherwise ``False``.
        username (str):

    Emits:
        valueChanged (tuple[int]):
            Tuple whose first and only item is the new value.
            Emitted during initialization of the hardware object
            and when setting a new value.
        limitsChanged (tuple[tuple[int, int]]):
            Tuple whose first and only item is a two-item tuple of the new limits
            (low limit first and high limit second).
            Emitted by ``update_limits`` if limit values are changed.
        stateChanged (tuple):
            Tuple whose first and only item is the new state.
            Emitted by ``force_emit_signals``
    """

    __metaclass__ = abc.ABCMeta

    unit = None

    def __init__(self, name: str):
        super().__init__(name)
        self._nominal_value = None
        self._nominal_limits = (None, None)
        self.actuator_name = None
        self.read_only = False
        self.default_value = None
        self.username = None
        self._lock = RLock()

    def init(self):
        """Init properties: actuator_name, username, read_only and default_value."""
        self.actuator_name = self.get_property("actuator_name")
        self.read_only = self.get_property("read_only") or False
        self.default_value = self.get_property("default_value")
        if self.default_value is not None:
            self.update_value(self.default_value)
        limits = self.get_property("default_limits")
        if limits:
            try:
                self._nominal_limits = tuple(literal_eval(limits))
            except TypeError:
                print("Invalid limits")
        self.username = self.get_property("username")

    @abc.abstractmethod
    def get_value(self):
        """Read the actuator position.

        Returns:
            Actuator position.
        """
        return None

    def get_limits(self):
        """Return actuator low and high limits.

        Returns:
            (tuple): Two-item tuple (low limit, high limit).
        """
        return self._nominal_limits

    def set_limits(self, limits: tuple) -> None:
        """Set actuator low and high limits and emit signal ``limitsChanged``.

        Args:
            limits (tuple): Two-item tuple (low limit, high limit).

        Raises:
            ValueError: Attempt to set limits for read-only actuator.
        """
        if self.read_only:
            raise ValueError("Attempt to set limits for read-only Actuator")

        self._nominal_limits = limits
        self.emit("limitsChanged", (self._nominal_limits,))

    def validate_value(self, value) -> bool:
        """Check if the value is within limits.

        Args:
            value(numerical): Value.

        Returns:
            ``True`` if within the limits, ``False`` otherwise.
        """
        if value is None:
            return True
        if math.isnan(value) or math.isinf(value):
            return False
        if None in self._nominal_limits:
            return True
        return self._nominal_limits[0] <= value <= self._nominal_limits[1]

    @abc.abstractmethod
    def _set_value(self, value):
        """Implementation of specific set actuator logic.

        Args:
            value: Target value.
        """

    def set_value(self, value, timeout: float = 0) -> None:
        """Set actuator to value.

        If ``timeout == 0``: return at once and do not wait (default).
        If ``timeout is None``: wait forever.

        Args:
            value: target value
            timeout (float): Optional timeout in seconds. Default is ``0``: do not wait.

        Raises:
            ValueError: Invalid value or attemp to set read only actuator.
            RuntimeError: Timeout waiting for status ready (from ``wait_ready``):
        """

        with self._lock:
            if self.read_only:
                raise ValueError("Attempt to set value for read-only Actuator")
            if self.validate_value(value):
                self._set_value(value)
                self.update_value()
                if timeout == 0:
                    return
                self.wait_ready(timeout)
            else:
                raise ValueError(f"Invalid value {value}")

    def update_value(self, value=None) -> None:
        """Check if the value has changed and emit signal ``valueChanged``.

        Args:
            value: Value.
        """
        if value is None:
            value = self.get_value()

        if self._nominal_value != value:
            self._nominal_value = value
            self.emit("valueChanged", (value,))

    def update_limits(self, limits=None) -> None:
        """Check if the limits have changed and emit signal ``limitsChanged``.

        Args:
            limits (tuple): Two-item tuple (low limit, high limit).
        """
        if not limits:
            limits = self.get_limits()

        if self._nominal_limits != limits:
            # All values are not NaN
            if not any(isinstance(lim, float) and math.isnan(lim) for lim in limits):
                self._nominal_limits = limits
                self.emit("limitsChanged", (limits,))

    def re_emit_values(self) -> None:
        """Update values for all internal attributes."""
        self.update_value(self.get_value())
        self.update_limits(self.get_limits())
        super(AbstractActuator, self).re_emit_values()

    def force_emit_signals(self) -> None:
        """Force emission of all signals.

        Method is called from GUI.
        Do not call it from within a hardware object.
        """
        self.emit("valueChanged", (self.get_value(),))
        self.emit("limitsChanged", (self.get_limits(),))
        self.emit("stateChanged", (self.get_state(),))

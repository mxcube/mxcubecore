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

"""
Defines the interface for N state devices
"""

import abc
from enum import Enum, unique
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)


__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


@unique
class InOutEnum(Enum):
    "In/Out"
    IN = "IN"
    OUT = "OUT"


@unique
class OpenCloseEnum(Enum):
    "Open/Close"
    OPEN = "OPEN"
    CLOSE = "CLOSED"


@unique
class OnOffEnum(Enum):
    "On/Off"
    ON = "ON"
    OFF = "OFF"


class AbstractNState(AbstractActuator):
    """
    Abstract base class for N state objects.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        AbstractActuator.__init__(self, name)
        self.predefined_values = {}
        self.state_definition = None
        self._valid = False

    def init(self):
        """Initialise some parametrs."""
        self.predefined_values = self.get_predefined_values()
        _valid = []

        self.state_definition = self.getProperty("state_definition", None)

        for value in self.predefined_values.keys():
            _valid.append(
                self._validate_value(value.upper(), self.state_definition.__members__)
            )

        if all(_valid) and len(_valid) == len(self.state_definition.__members__):
            self._valid = True

        if self.state_definition in ["IntEnum", "StrEnum", "FloatEnum"]:
            self.state_definition = Enum(self.state_definition, self.predefined_values)
        else:
            self.state_definition = globals().get(self.state_definition, None)

        if not (self.state_definition or self._valid):
            raise ValueError("Mistmatching predefined values")

    def _validate_value(self, value, values=None):
        """Check if the value is within specified values.
        Args:
            value: value
            values(tuple): tuple of values.
        Returns:
            (bool): True if within the values
        """
        if not values:
            values = self.predefined_values.keys()
        return value in values

    def get_predefined_values(self):
        """Get the predefined values
        Returns:
            (dict): Dictionary of predefined {name: value}
        """
        predefined_values = {}
        for value in self["predefined_value"]:
            try:
                predefined_values.update(
                    {value.getProperty("name"): value.getProperty("value")}
                )
            except AttributeError:
                pass

        return predefined_values

    def set_limits(self, limits):
        """Set actuator low and high limits.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        raise NotImplementedError

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emits signal limitsChanged.
        Args:
            limits (tuple): two floats tuple (low limit, high limit).
        """
        raise NotImplementedError

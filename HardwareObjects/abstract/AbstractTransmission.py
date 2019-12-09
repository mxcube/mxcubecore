# -*- coding: utf-8 -*-
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

"""Base class for transmission control."""

import abc
from HardwareRepository.HardwareObject.abstract.AbstractMotor import AbstractMotor

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractTransmission(AbstractMotor):
    """
    Base class for transmission control by filters, slits, apertures or other means
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self._value = None
        self._limits = [0, 100]
        self._state = None

    def _set_value(self, value, wait=True, timeout=None):
        """Set transmission to absolute level in percent.
           Wait for the move  of all acutators to finish by default.
        Args:
            value (float): target position
            wait (bool): optional - wait until all movements finished.
            timeout (float): optional - timeout [s].
        """
        self._value = value
        self.emit("valueChanged", self._value)

    @abc.abstractmethod
    def get_value(self):
        """Get the current transmission in percents
        Returns:
            float: current transmission level.
        """
        return None

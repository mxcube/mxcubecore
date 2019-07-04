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

"""
Example of Transmission HardwareObject using new StandardHardwareObject
Based on existing HardwarObjects.Transmission
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import gevent

from HardwareRepository.HardwareObjects.abstract import AbstractActuator2

__credits__ = [" Copyright © 2019 - by MXCuBE collaboration. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "17/05/2019"


class StandardMockupObject(AbstractActuator2.StandardHardwareObject):
    """MockTransmission implementation using new StandardHardwareObject
    """

    def __init__(self, name):
        super(StandardMockupObject, self).__init__(name)

        self._value = None
        self._limits = (None, None)
        self._value_set_delay = 1.0

    def get_value(self):
        """Get current value

        Returns:
            Optional[float]
        """
        return self._value

    def _set_value(self, value):

        gevent.spawn(self._delayed_set_value, value, self._value_set_delay)

    def _set_limits(self, limits):
        """Set value limits to (lowerbound, upperlound)

        Args:
            limits (Tuple[Optional[float], Optional[float]]): limits to set

        Returns:

        """
        self._limits = tuple(limits)
        self.emit("limitsChanged", (limits,))

    def _delayed_set_value(self, value, delay):
        """Set value after delay, to mimick hardware operation

        Args:
            value (Optional[float]): New value
            delay (float): delay time in seconds.

        Returns:

        """
        self.set_state(self.STATE.BUSY)
        gevent.sleep(delay)
        self._value = value
        self.set_state(self.STATE.READY)
        self.emit("valueChanged", self.value)

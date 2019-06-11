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

from HardwareRepository.HardwareObjects.abstract import StandardHardwareObject

__credits__ = [" Copyright © 2016 - 2019 by Global Phasing Ltd. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "17/05/2019"


class StandardMockupObject(StandardHardwareObject.StandardHardwareObject):
    """MockTransmission implementation using new StandardHardwareObject
    """

    def __init__(self, name):
        super(StandardMockupObject, self).__init__(name)

        self._value = None
        self._limits = (None, None)
        self._value_set_delay = 1.0

    @property
    def value(self):
        """
        Returns current transmission in %
        :return: float (0 - 100)
        """
        return self._value

    @value.setter
    def value(self, value):
        """
        Sets transmission.  NB actual value set may differ from input value
        :param value: float (0 - 100)
        :return:
        """

        if self.accept_new_value(value):
            gevent.spawn(self._delayed_set_value, value, self._value_set_delay)

    def _set_limits(self, value):
        """
        Sets transmission limits
        :param value: Sequence[float] # length two
        :return:
        """
        self._limits = tuple(value)

    def _delayed_set_value(self, value, delay):
        """

        :param value: Optional[float]
        :param delay: float, delay time in seconds.
        :return:
        """
        gevent.sleep(delay)
        self._value = value
        self.state = self.STATE.READY
        self.emit("valueChanged", self.value)

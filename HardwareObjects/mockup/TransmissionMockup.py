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
Example of Transmission HardwareObject using new AbstractTransmission
Based on existing HardwarObjects.Transmission
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import gevent

from HardwareRepository.HardwareObjects.abstract import AbstractTransmission

__credits__ = [" Copyright © 2016 - 2019 by Global Phasing Ltd. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "17/05/2019"


class TransmissionMockup(AbstractTransmission.AbstractTransmission):
    """MockTransmission implementation using new AbstractTransmission
    """

    def __init__(self, name):
        super(TransmissionMockup, self).__init__(name)

        self._transmission = None
        self._state = None
        self._limits = (None, None)

    def init(self):
        # NB should be set from configuration
        self._transmission = 100
        self._state = self.STATE.READY
        self._limits = (0, 100)

        self.update_values()

    def get_transmission(self):
        """
        Returns current transmission in %
        :return: float (0 - 100)
        """
        return self._transmission

    def _set_transmission(self, value):
        """
        Sets transmission.  NB actual value set may differ from input value
        :param value: float (0 - 100)
        :param timeout: timeout is seconds. If None function will not wait
        :return:
        """
        delay = 2.0
        self._state = self.STATE.MOVING
        self.emit("stateChanged", self.STATE.MOVING)
        self._transmission = value

        def delayed_state_change(self, delay):
            # Function to dellay state_change till after _set_transmission returns
            gevent.sleep(delay)
            self._state = self.STATE.READY
            self.emit("stateChanged", self.STATE.READY)
            self.emit("transmissionChanged", self.get_transmission())
        gevent.spawn(delayed_state_change, self, delay)

    def get_limits(self):
        """
        Returns transmission limits as a tuple of two floats
        :return: Tuple[float, float]
        """
        return self._limits

    def _set_limits(self, value):
        """
        Sets transmission limits
        :param value: Sequence[float] # length two
        :return:
        """
        self._limits = tuple(value)

    def get_state(self):
        """
        Returns current transmission state
        :return: STATE
        """
        return self._state


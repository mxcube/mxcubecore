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

from HardwareRepository.HardwareObjects.mockup import AbstractMockActuator

__credits__ = [" Copyright © 2019 -  by MXCuBE collaboration. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "17/05/2019"


class TransmissionMockup(AbstractMockActuator.StandardMockupObject):
    """MockTransmission implementation using new StandardHardwareObject
    """

    def init(self):
        # NB should be set from configuration
        self.value_resolution = 0.01
        self._limits = (0, 100)
        self._value_set_delay = 2.0
        self._value = 100
        self._state =self.STATE.READY

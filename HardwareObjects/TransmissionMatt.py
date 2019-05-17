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

import api
from HardwareRepository.HardwareObjects.abstract import AbstractTransmission
from PyTransmission import matt_control

__credits__ = [" Copyright © 2016 - 2019 by Global Phasing Ltd. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "17/05/2019"


class Transmission(AbstractTransmission.AbstractTransmission):
    """Example of Transmission implementation using new AbstractTransmission

    Based on pre-existing HardwarObjects.Transmission
    """

    def __init__(self, name):
        super(Transmission, self).__init__(name)

        self._limits = (None, None)
        self.__matt = None

        # Example of maps from channel states to self.STATE states.
        # Note that numbers need not match,
        # and several input states can map to same output state
        STATE = self.STATE
        self.__matt_state_to_state = {
            0: STATE.UNKOWN,
            1: STATE.READY,
            4: STATE.MOVING,
            6: STATE.MOVING,
            -1: STATE.FAULT,
            -2: STATE.ERROR,
        }

    def init(self):

        self.__matt = matt_control.MattControl(
            self.getProperty("wago_ip"),
            len(self["filter"]),
            0,
            self.getProperty("type"),
            self.getProperty("alternate"),
            self.getProperty("status_module"),
            self.getProperty("control_module"),
            self.getProperty("datafile"),
        )
        self.__matt.connect()

        # NB should be set from configuration
        self._limits = (0, 100)

        self.update_values()

    def get_transmission(self):
        """
        Returns current transmission in %
        :return: float (0 - 100)
        """
        self.__matt.set_energy(api.energy.get_current_energy())
        return self.__matt.transmission_get()

    def _set_transmission(self, value):
        """
        Sets transmission.  NB actual value set may differ from input value
        :param value: float (0 - 100)
        :return:
        """
        # NB These functions should emit stateChanged and transmissionChanged
        # At appropriate times, i.e. when the changes are done,
        # even if this is after this function has returned.

        self.__matt.set_energy(api.energy.get_current_energy())
        self.__matt.transmission_set(value)

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
        self.emit("limitsChanged", (value,))

    def get_state(self):
        """
        Returns current transmission state
        :return: STATE
        """
        return self._state_map.get(self.__matt.GETSTATESOMEHOW(), self.STATE.UNKOWN)

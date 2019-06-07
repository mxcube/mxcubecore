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

"""Defines abstract Transmission - example of an abstract class
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
import gevent
from HardwareRepository.BaseHardwareObjects import HardwareObject

# We should make a standard set of states and use that wherever possible
from somewhere import GeneralState

__credits__ = [" Copyright © 2019 by MXCuBE collaboration. All rights reserved"]
__license__ = "LGPLv3+"
__category__ = "General"
__author__ = "rhfogh"
__date__ = "20190607"


class AbstractTransmission(HardwareObject):
    """Abstract transmission"""

    __metaclass__ = ABCMeta

    STATE = GeneralState

    def __init__(self, name):
        super(AbstractTransmission, self).__init__(name)

    def set_value_to(self, value, timeout=None):
        """
        Sets value and waits for completion.
        NB actual value set may differ from input value

        :param value: float (0 - 100)
        :param timeout: float
        :return:
        """
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Invalid value for timeout: %s" % timeout)
        gevent.with_timeout(timeout, setattr, self, value)


        limits = self.get_limits()
        if None not in limits and (value >= limits[0]) != (value <= limits[1]):
            raise ValueError("transmission value %s outside imits %s" % (value, limits))
        if timeout is None:
            self._set_transmission(value)
        else:
            gevent.with_timeout(timeout, self._set_transmission, value)

    def set_limits(self, value):
        """
        Sets transmission limits
        :param value: sequence of two floats
        :return:
        """
        if None not in value:
            value = sorted(value)
        self._set_limits(value)

    def update_values(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("limitsChanged", (self.get_limits(),))
        self.emit("transmissionChanged", self.get_transmission())
        self.emit("stateChanged", self.get_state())

    def is_ready(self):
        """
        Is Transmission ready?
        :return: bool
        """
        return self.get_state() is self.STATE.READY

    def wait_ready(self, timeout=None):
        """
        Wait up to timeout s till device is ready
        :param timeout: period to wait (in s) before returning, default to config value
        :return:
        """
        if timeout is None:
            timeout = self.getProperty("default_timeout", 20)
        with gevent.Timeout(
            timeout,
            Exception("%s: Timeout waiting for ready" % self.__class__.__name__),
        ):
            while self.get_state() is not self.STATE.READY:
                gevent.sleep(0.1)

    @abstractmethod
    def init(self):
        """Set up initial values and call update_values"""

    @abstractmethod
    def get_transmission(self):
        """
        Returns current transmission in %
        :return: float (0 - 100)
        """

    @abstractmethod
    def _set_transmission(self, value):
        """
        Sets transmission.  NB actual value set may differ from input value
        :param value: float (0 - 100)
        :return:
        """

    @abstractmethod
    def get_limits(self):
        """
        Returns transmission limits as a tuple of two floats
        :return: Tuple[float, float]
        """

    @abstractmethod
    def _set_limits(self, value):
        """
        Sets transmission limits
        :param value: Sequence[float] # length two
        :return:
        """

    @abstractmethod
    def get_state(self):
        """
        Returns current transmission state
        :return: STATE
        """


# NB It does not make sense to have a set_state function
# Since you cannot tell a motor taht it is moving - you tell it to move
# The underlying implementation must set teh state as appropriate

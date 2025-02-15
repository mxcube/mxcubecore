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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

""" """

import abc
from warnings import warn

from mxcubecore.BaseHardwareObjects import HardwareObject

__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3"


class AbstractSlits(HardwareObject, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, *args):
        warn(
            "AbstractSlits is deprecated. Use specific motors instead",
            DeprecationWarning,
        )
        HardwareObject.__init__(self, *args)

        self._value = [None, None]
        self._min_limits = [None, None]
        self._max_limits = [None, None]
        self._status = [None, None]

    def get_horizontal_gap(self):
        """
        Returns horizontal gap in microns
        :return: float
        """
        return self._value[0]

    @abc.abstractmethod
    def set_horizontal_gap(self, value, timeout=None):
        """
        Sets vertical gap in microns
        :param value: target value
        :param timeout: timeout is sec. If None do not wait
        :return:
        """
        pass

    def get_vertical_gap(self):
        """
        Returns vertical gap in microns
        :return: float
        """
        return self._value[1]

    @abc.abstractmethod
    def set_vertical_gap(self, value, timeout=None):
        """
        Sets vertical gap in microns
        :param value: float
        :param timeout: timeout in sec. If None do not wait
        :return:
        """
        pass

    def get_gaps(self):
        """
        Returns horizontal and vertical gaps
        :return: list of two floats
        """
        return self._value

    @abc.abstractmethod
    def stop_horizontal_gap_move(self):
        """
        Stops horizontal gap movement
        :return:
        """
        return

    @abc.abstractmethod
    def stop_vertical_gap_move(self):
        """
        Stops vertical gap movement
        :return:
        """
        return

    def get_min_limits(self):
        """
        Returns min limits
        :return: list of two floats
        """
        return self._min_limits

    def set_min_limits(self, new_limits):
        """
        Sets minimal gap limits
        :param new_limits: list of two floats
        :return:
        """
        if new_limits is not None:
            self._min_limits = new_limits
            self.emit("minLimitsChanged", self._min_limits)

    def get_max_limits(self):
        """
        Return max limits
        :return: list of two floats
        """
        return self._max_limits

    def set_max_limits(self, new_limits):
        """
        Sets maximal gap limits
        :param new_limits:
        :return:
        """
        if new_limits is not None:
            self._max_limits = new_limits
            self.emit("maxLimitsChanged", self._max_limits)

    def force_emit_signals(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("valueChanged", self._value)
        self.emit("minLimitsChanged", self._min_limits)
        self.emit("maxLimitsChanged", self._max_limits)
        self.emit("statusChanged", self._status)

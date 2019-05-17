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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Defines abstract attenuators (transmission)
"""

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class AbstractAttenuators(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.__transmission_value = None
        self.__transmission_limits = None
        self.__transmission_state = None

    def get_transmission(self):
        """
        Returns current transmission in %
        :return: float (0 - 100)
        """
        return self.__transmission_value

    def set_transmission(self, value, timeout=None):
        """
        Sets transmission
        :param value: float (0 - 100)
        :param timeout: timeout is secons
        :return:
        """
        self.__transmission_value = value
        self.emit("transmissionChanged", self.__transmission_value)

    def get_limits(self):
        """
        Returns transmission limits as a list of two floats
        :return: list
        """
        return self.__transmission_limits

    def set_limits(self, limits):
        """
        Sets transmission limits
        :param limits: list of two floats
        :return:
        """
        self.__transmission_limits = limits
        self.emit("limitsChanged", (self.__transmission_limits,))

    def get_state(self):
        """
        Returns current transmission state
        :return: str
        """
        return self.__transmission_state

    def set_state(self, state):
        """
        Sets transmission state
        :param state: str
        :return:
        """
        self.__transmission_state = state
        self.emit("stateChanged", self.__transmission_state)

    def update_values(self):
        """
        Reemits all signals
        :return:
        """
        self.emit("transmissionChanged", self.get_transmission())
        self.emit("limitsChanged", (self.get_limits(),))
        self.emit("stateChanged", self.get_state())

    transmission_value = property(get_transmission, set_transmission, doc="Transmission in % (0 - 100)")
    transmission_limits = property(get_limits, set_limits, doc="Transmission limits as list of two floats")
    transmission_state = property(get_state, set_state, doc="State as str")

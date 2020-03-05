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

"""AbstractBeam"""

import abc
from enum import Enum, unique
from HardwareRepository.HardwareObjects.abstract.AbstractActuator import (
    AbstractActuator,
)

__credits__ = """MXCuBE collaboration"""
__license__ = "LGPLv3+"
__category__ = "General"


class AbstractBeam(AbstractActuator):
    """
    Abstract base class for beam objects.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        AbstractActuator.__init__(self, name)

        self._aperture = None
        self._slits = None

        self._nominal_value = [None, None]
        self._size_dict = {"slits": [None, None],
                           "aperture": [None, None]}
        self._screen_position = [None, None]
        self._shape = ""
        self._divergence = (None, None)
        self._info_dict = {"size_x": self._nominal_value[0],
                           "size_y": self._nominal_value[1],
                           "shape": self._shape,
                           "position": self._screen_position
        }

    @property
    def aperture(self):
        return self._aperture

    @property
    def slits(self):
        return self._slits

    def get_divergence(self):
        """Returns beam horizontal beam divergence

        :return: tuple
        """
        return self._divergence[0], self._divergence[1]

    def get_screen_position(self):
        """Returns beam mark position on a screen

        :return: [float, float]
        """
        return self._screen_position[0], self._screen_position[1]

    def get_size(self):
        return self.get_value()

    def get_value(self):
        """Returns beam size in microns

        :return: Tuple(int, int)
        """
        return self._nominal_value[0], self._nominal_value[1]

    def _set_value(self, value):
        self._nominal_value = value
        self.emit("beamSizeChanged", self._nominal_value)

    def get_shape(self):
        """Returns beam shape

        :return: beam shape as str
        """
        return self._shape

    def get_info_dict(self):
        return self._info_dict

    def get_slits_gap(self):
        return self._size_dict["slits"][0], self._size_dict["slits"][1]

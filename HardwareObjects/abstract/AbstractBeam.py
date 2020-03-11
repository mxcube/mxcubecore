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
Beam abstract class - methods to define the size and shape of
the beam, its presence.
"""

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


import abc
from enum import Enum, unique
from HardwareRepository.BaseHardwareObjects import HardwareObject


@unique
class BeamShape(Enum):
    """ Beam shape definitions """

    UNKNOWN = "unknown"
    RECTANGULAR = "rectangular"
    ELIPTICAL = "ellipse"


class AbstractBeam(HardwareObject):
    """ AbstractBeam class """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.beam_width = None
        self.beam_height = None
        self.beam_shape = BeamShape.UNKNOWN
        self.beam_label = None
        self.default_beam_divergence = None
        self.beam_position = (None, None)

    def init(self):
        """Initialise default values and objects"""
        _divergence_vertical = self.getProperty("beam_divergence_vertical")
        _divergence_horizontal = self.getProperty("beam_divergence_horizontal")
        self.default_beam_divergence = (_divergence_horizontal, _divergence_vertical)
        self.beam_position = (0, 0)

    def get_beam_divergence(self):
        """Get the beam dicergence.
        Returns:
            (tuple): Beam divergence (horizontal, vertical) [μm]
        """
        if self.beam_definer:
            return self.beam_definer.get_divergence()
        else:
            return self.default_beam_divergence

    def get_value(self):
        """ Get the size (width and heigth) of the beam and its shape.
        Retunrs:
            (float, float, Enum, str): Width, heigth, shape and label.
        Raises:
            NotImplementedError
        """
        return self.beam_width, self.beam_heigth, self.beam_shape, self.beam_label

    def get_availble_size(self):
        """ Get the available predefined beam definers configuration.
        Returns:
            (dict): Dictionary {"type": (list), "values": (list)}, where
               "type": the definer type
               "values": List of available beam size difinitions,
                         according to the "type". 
        Raises:
            NotImplementedError
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _set_value(self, size=None):
        """Set the beam size
        Args:
            size (list): Width, heigth or
                  (str): Position name
        """

    def set_value(self, size=None):
        """Set the beam size
        Args:
            size (list): Width, heigth or
                  (str): Position name
        """
        self._set_value(size)
        self.update_value()

    def get_beam_position(self):
        """Get the beam position
        Returns:
            (tuple): Position (x, y) [pixel]
        """
        return self.beam_position

    def set_beam_position(self, beam_x_y):
        """Set the beam position
        Returns:
            beam_x_y (tuple): Position (x, y) [pixel]
        """
        raise NotImplementedError

    def update_value(self):
        """Check if the value has changed. Emist signal valueChanged."""
        _value = self.get_value()
        self.emit("valueChanged", (_value))

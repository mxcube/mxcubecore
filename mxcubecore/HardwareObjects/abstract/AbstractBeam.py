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

__copyright__ = """MXCuBE collaboration"""
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

        self._aperture = None
        self._slits = None
        self._definer = None

        self._beam_size_dict = {}
        self._beam_width = None
        self._beam_height = None
        self._beam_shape = BeamShape.UNKNOWN
        self._beam_label = None
        self._beam_divergence = (None, None)
        self._beam_position_on_screen = [None, None]

        self._beam_info_dict = {"size_x": self._beam_width,
                                "size_y": self._beam_height,
                                "shape": self._beam_shape,
                                "label": self._beam_label}


    def init(self):
        """Initialise default values and objects"""
        _divergence_vertical = self.getProperty("beam_divergence_vertical")
        _divergence_horizontal = self.getProperty("beam_divergence_horizontal")
        self._beam_divergence = (_divergence_horizontal, _divergence_vertical)
        self._beam_position_on_screen = (0, 0)

    @property
    def aperture(self):
        """
        """
        return self._aperture

    @property
    def slits(self):
        """
        """
        return self._slits

    @property
    def definer(self):
        return self._definer

    def evaluate_beam_info(self):
        """
        Evaluates beam parameters and updates beam info dict

        Returns:
            (dict): self._beam_info_dict

        """
        return self._beam_info_dict

    def get_beam_divergence(self):
        """Get the beam divergence.
        Returns:
            (tuple): Beam divergence (horizontal, vertical) [μm]
        """
        if self._definer:
            return self._definer.get_divergence()
        else:
            return self._beam_divergence

    def get_available_size(self):
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

    def get_beam_shape(self):
        """
        Returns:
            beam_shape: Enum BeamShape
        """
        return self._beam_shape

    def get_beam_size(self):
        """

        Returns:
            (tuple): two floats
        """
        return self._beam_width, self._beam_height

    def get_beam_position_on_screen(self):
        """Get the beam position
        Returns:
            (tuple): Position (x, y) [pixel]
        """
        #TODO move this method to AbstractSampleView
        return self._beam_position_on_screen

    def set_beam_position_on_screen(self, beam_x_y):
        """Set the beam position
        Returns:
            beam_x_y (tuple): Position (x, y) [pixel]
        """
        raise NotImplementedError

    def get_beam_info_dict(self):
        """

        Returns:
            (dict): copy of beam_info_dict
        """
        return self._beam_info_dict.copy()

    def update_value(self, value=None):
        """Check if the value has changed. Emist signal valueChanged."""
        if value is None:
            value = self.get_value()
        self.emit("valueChanged", (value,))

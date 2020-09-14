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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
AbstracBeam class - methods to define the size and shape of the beam, its presence.

emits:
- beamSizeChanged (self._beam_width, self._beam_height)
- beamInfoChanged (self._beam_info_dict.copy())
"""

__copyright__ = """ Copyright © 2016 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import abc
import sys
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

        self._beam_size_dict = {
            "aperture": [sys.float_info.max, sys.float_info.max],
            "slits": [sys.float_info.max, sys.float_info.max],
        }
        self._beam_width = None
        self._beam_height = None
        self._beam_shape = BeamShape.UNKNOWN
        self._beam_label = None
        self._beam_divergence = (None, None)
        self._beam_position_on_screen = [None, None]  # TODO move to sample_view

        self._beam_info_dict = {
            "size_x": self._beam_width,
            "size_y": self._beam_height,
            "shape": self._beam_shape,
            "label": self._beam_label,
        }

    def init(self):
        """
        Initialise default values and objects
        """
        _divergence_vertical = self.get_property("beam_divergence_vertical")
        _divergence_horizontal = self.get_property("beam_divergence_horizontal")
        self._beam_divergence = (_divergence_horizontal, _divergence_vertical)
        self._beam_position_on_screen = (0, 0)

    @property
    def aperture(self):
        """
        Returns aperture hwobj
        """
        return self._aperture

    @property
    def slits(self):
        """
        Returns slits hwobj
        """
        return self._slits

    @property
    def definer(self):
        """
        Beam definer device, equipment like focusing optics, CRLs, and etc.
        """
        return self._definer

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
        """Get the available predefined beam definers configuration.
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
        self.evaluate_beam_info()
        return self._beam_shape

    def get_beam_size(self):
        """
        Returns:
            (tuple): two floats
        """
        self.evaluate_beam_info()
        return self._beam_width, self._beam_height

    def set_beam_size_shape(self, beam_width, beam_height, beam_shape):
        """
        Sets beam size and shape
        Args:
            beam_width (float): requested beam width in microns
            beam_height (float): requested beam height in microns
            beam_shape (BeamShape enum): requested beam shape
        """
        if beam_shape == BeamShape.RECTANGULAR:
            self._slits.set_horizontal_gap(beam_width)
            self._slits.set_vertical_gap(beam_height)
        elif beam_shape == BeamShape.ELIPTICAL:
            self._aperture.set_diameter_size(beam_width)

    def get_beam_position_on_screen(self):
        """Get the beam position
        Returns:
            (tuple): Position (x, y) [pixel]
        """
        # TODO move this method to AbstractSampleView
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

    def evaluate_beam_info(self):
        """
        Method called if aperture, slits or focusing has been changed
        Returns: dictionary, {size_x: 0.1, size_y: 0.1, shape: BeamShape enum}
        """

        size_x = min(
            self._beam_size_dict["aperture"][0], self._beam_size_dict["slits"][0],
        )
        size_y = min(
            self._beam_size_dict["aperture"][1], self._beam_size_dict["slits"][1],
        )

        self._beam_width = size_x
        self._beam_height = size_y

        if tuple(self._beam_size_dict["aperture"]) < tuple(
            self._beam_size_dict["slits"]
        ):
            self._beam_shape = BeamShape.ELIPTICAL
        else:
            self._beam_shape = BeamShape.RECTANGULAR

        self._beam_info_dict["size_x"] = size_x
        self._beam_info_dict["size_y"] = size_y
        self._beam_info_dict["shape"] = self._beam_shape

        return self._beam_info_dict

    def emit_beam_info_change(self):
        """
        Reemits beamSizeChanged and beamInfoChanged signals
        """
        if self._beam_width != 9999 and self._beam_height != 9999:
            self.emit("beamSizeChanged", (self._beam_width, self._beam_height))
            self.emit("beamInfoChanged", (self._beam_info_dict))

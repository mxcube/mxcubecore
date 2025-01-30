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

"""Abstract beam hardware object."""

from __future__ import annotations

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import abc
import sys
from enum import (
    Enum,
    unique,
)
from warnings import warn

from mxcubecore.BaseHardwareObjects import HardwareObject


@unique
class BeamShape(Enum):
    """Beam shape definitions"""

    UNKNOWN = "unknown"
    RECTANGULAR = "rectangular"
    ELLIPTICAL = "ellipse"


class AbstractBeam(HardwareObject):
    """Abstract beam hardware object.

    Has methods to define the size and shape of the beam.

    Emits:
        beamSizeChanged(tuple[float, float]):
            Two-item tuple of beam width and beam height in micrometers
            emitted when the beam size has changed.
        beamInfoChanged(dict):
            Dictionary containing beam info emitted when the beam info has changed.

    Attributes:
        _aperture: reference to the aperture hardware object
        _slits: reference to the slits hardware object
        _definer: reference to the slits hardware object
        _beam_size_dict (dict): dictionary containing min max of aperure, slits and definer
        _beam_width (float): beam size in horizontal direction
        _beam_height (float): beam size in vertical direction
        _beam_shape (str): beam shape (rectangular, ellipse, unknown)
        _beam_divergence (tuple): beam divergence in horizontal and vertical directions
        _beam_position_on_screen (tuple): beam position in pixel units
        _beam_info_dict (dict): dictionary containing size_x, size_y, shape, label
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name) -> None:
        super().__init__(name)

        self._aperture = None
        self._slits = None
        self._definer = None
        self._definer_type = None

        self._beam_size_dict = {
            "aperture": [sys.float_info.max, sys.float_info.max],
            "slits": [sys.float_info.max, sys.float_info.max],
            "definer": [sys.float_info.max, sys.float_info.max],
        }
        self._beam_width = None
        self._beam_height = None
        self._beam_shape = BeamShape.UNKNOWN
        self._beam_label = None
        self._beam_divergence = (None, None)
        self._beam_position_on_screen = [None, None]

        self._beam_info_dict = {
            "size_x": self._beam_width,
            "size_y": self._beam_height,
            "shape": self._beam_shape,
            "label": self._beam_label,
        }

    def init(self) -> None:
        """Initialise default values and objects."""
        super().init()
        _divergence_vertical = self.get_property("beam_divergence_vertical")
        _divergence_horizontal = self.get_property("beam_divergence_horizontal")
        self._beam_divergence = (_divergence_horizontal, _divergence_vertical)
        self._beam_position_on_screen = [0, 0]
        self._definer_type = self.get_property("definer_type")

    @property
    def aperture(self):
        """Aperture hardware object."""
        return self._aperture

    @property
    def slits(self):
        """Slits hardware object."""
        return self._slits

    @property
    def definer(self):
        """Beam definer device, equipment like focusing optics, CRLs, and etc."""
        return self._definer

    def get_beam_divergence(self) -> tuple:
        """Get the beam divergence.

        Returns:
            Beam divergence (horizontal, vertical) in micrometers.
        """
        return self._beam_divergence

    def get_available_size(self) -> dict:
        """Get the available beam definers configuration.

        Returns:
            Dictionary ``{"type": (list), "values": (list)}`` where
            ``type`` is the definer type ``("aperture", "slits","definer")`` and
            ``values`` is a list of available beam size definitions
            according to ``type``.
        """
        raise NotImplementedError

    def get_defined_beam_size(self) -> dict:
        """Get the predefined beam labels and size.

        Returns:
            Dictionary with list of available beam size labels
            and the corresponding size (width,height) tuples.
            ``{"label": [str, str, ...], "size": [(w,h), (w,h), ...]}``.
        """
        raise NotImplementedError

    def get_beam_shape(self) -> BeamShape:
        """Get beam shape.

        Returns:
            Beam shape.
        """
        self.evaluate_beam_info()
        return self._beam_shape

    def get_beam_size(self) -> tuple[float, float]:
        """Get beam size.

        Returns:
            Two-item tuple: width and height.
        """
        self.evaluate_beam_info()
        return self._beam_width, self._beam_height

    def set_value(self, size: list[float] | str | None = None) -> None:
        """Set the beam size.
        Args:
            size: List of width and heigth in micrometers or
                aperture or definer name as string.
        """
        raise NotImplementedError

    def set_beam_size_shape(
        self,
        beam_width: float,
        beam_height: float,
        beam_shape: BeamShape,
    ) -> None:
        """Set beam size and shape.

        Args:
            beam_width: Requested beam width in microns.
            beam_height: Requested beam height in microns.
            beam_shape: Requested beam shape.
        """
        warn(
            "set_beam_size_shape is deprecated. Use set_value() instead",
            DeprecationWarning,
        )

        if beam_shape == BeamShape.RECTANGULAR:
            self._slits.set_horizontal_gap(beam_width)
            self._slits.set_vertical_gap(beam_height)
        elif beam_shape == BeamShape.ELLIPTICAL:
            self._aperture.set_diameter_size(beam_width)

    def get_beam_position_on_screen(self) -> tuple:
        """Get the beam position.

        Returns:
            X and Y coordinates of the beam position in pixels.
        """
        # (TODO) move this method to AbstractSampleView
        return self._beam_position_on_screen

    def set_beam_position_on_screen(self, beam_x_y: tuple) -> None:
        """Set the beam position.

        Args:
            beam_x_y: X and Y coordinates of the beam position in pixels.
        """
        raise NotImplementedError

    def get_beam_info_dict(self) -> dict:
        """Get beam info dictionary.

        Returns:
            Copy of beam info dictionary.
        """
        return self._beam_info_dict.copy()

    def evaluate_beam_info(self) -> dict:
        """Method called if aperture, slits or focusing has been changed.

        Evaluates which of the beam size defining devices determins the size.

        Returns:
            Beam info dictionary ``dict``, type of the definer ``str``.
            ``{size_x: float, size_y: float, shape: BeamShape enum, label: str}``.
        """
        _shape = BeamShape.UNKNOWN
        _size = min(self._beam_size_dict.values())
        key = [k for k, v in self._beam_size_dict.items() if v == _size]

        if len(key) == 1:
            _label = key[0]
        else:
            if self._definer_type in key:
                _label = self._definer_type
            else:
                _label = "UNKNOWN"

        if _label == "slits":
            _shape = BeamShape.RECTANGULAR
        else:
            _shape = BeamShape.ELLIPTICAL

        self._beam_width = _size[0]
        self._beam_height = _size[1]
        self._beam_shape = _shape
        self._beam_info_dict["size_x"] = _size[0]
        self._beam_info_dict["size_y"] = _size[1]
        self._beam_info_dict["shape"] = _shape
        self._beam_info_dict["label"] = _label

        return self._beam_info_dict

    def re_emit_values(self):
        """Reemit ``beamSizeChanged`` and ``beamInfoChanged`` signals."""
        HardwareObject.re_emit_values(self)
        if self._beam_width != 9999 and self._beam_height != 9999:
            self.emit("beamSizeChanged", (self._beam_width, self._beam_height))
            self.emit("beamInfoChanged", (self._beam_info_dict))
            self.emit("beamPosChanged", (self._beam_position_on_screen,))

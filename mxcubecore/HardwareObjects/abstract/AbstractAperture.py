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


"""Abstract hardware object for the aperture."""

from __future__ import annotations

import logging
from warnings import warn

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractAperture(HardwareObject):
    """Abstract hardware object for the aperture.

    Emits:
        diameterIndexChanged (int, float):
            Two-item tuple: current index and diameter in millimeters.
        valueChanged (str):
            Current position name.
    """

    def __init__(self, name: str) -> None:
        warn(
            "AbstractAperture is deprecated. Use AbstractNState instead",
            DeprecationWarning,
        )
        HardwareObject.__init__(self, name)

        self._current_position_name = None
        self._current_diameter_index = None
        self._diameter_size_list = ()
        self._position_list = ()

    def init(self):
        try:
            self._diameter_size_list = eval(self.get_property("diameter_size_list"))
        except Exception:
            logging.getLogger("HWR").error("Aperture: no diameter size list defined")

        try:
            self._position_list = eval(self.get_property("position_list"))
        except Exception:
            logging.getLogger("HWR").error("Aperture: no position list defined")

    def get_diameter_size_list(self) -> list[float]:
        """Get list of diameter sizes.

        Returns:
            List of diameter sizes in microns.
        """
        return self._diameter_size_list

    def get_position_list(self) -> list[str]:
        """Get list of positions.

        Returns:
            Position names as a list of strings.
        """
        return self._position_list

    def get_diameter_index(self) -> int:
        """Get current diameter index.

        Returns:
            Current diameter index.
        """
        return self._current_diameter_index

    def set_diameter_index(self, diameter_index: int) -> None:
        """Set active diameter index.

        Args:
            diameter_index: Selected diameter index.
        """
        if diameter_index < len(self._diameter_size_list):
            self._current_diameter_index = diameter_index
            self.emit(
                "diameterIndexChanged",
                self._current_diameter_index,
                self._diameter_size_list[self._current_diameter_index] / 1000.0,
            )
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Diameter index %d is not valid" % diameter_index
            )

    def get_diameter_size(self) -> float:
        """Get diameter size.

        Returns:
            Current diameter size in millimeters.
        """
        return self._diameter_size_list[self._current_diameter_index]

    def set_diameter_size(self, diameter_size: int) -> None:
        """Set diameter size.

        Args:
            diameter_size: selected diameter index
        """
        if diameter_size in self._diameter_size_list:
            self.set_diameter_index(self._diameter_size_list.index(diameter_size))
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Selected diameter is not in the diameter list"
            )

    def get_position_name(self) -> str:
        """Get current position name.

        Returns:
            Current position name.
        """
        return self._current_position_name

    def set_position(self, position_index: int) -> None:
        warn(
            "set_position is deprecated. Use set_position_index(position_index) instead",
            DeprecationWarning,
        )
        self.set_position_index(position_index)

    def set_position_name(self, position_name: str) -> None:
        """Set aperture position based on a position name.

        Args:
            position_name: Selected position name.
        """
        if position_name in self._position_list:
            self._current_position_name = position_name
            self.emit("valueChanged", self._current_position_name)
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Position %s is not in the position list" % position_name
            )

    def set_position_index(self, position_index: int) -> None:
        """Set aperture position based on a position index.

        Args:
            position_index: Selected position index.
        """
        if position_index < len(self._position_list):
            self._current_position_name = self._position_list[position_index]
            self.emit("valueChanged", self._current_position_name)
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Selected position is not in the position list"
            )

    def set_in(self):
        """Set aperture in the beam."""

    def set_out(self):
        """Remove aperture from the beam."""

    def is_out(self) -> bool:
        """
        Returns:
            ``True`` if aperture is in the beam, otherwise returns ``False``.
        """

    def force_emit_signals(self) -> None:
        """Reemit all signals."""
        self.emit("valueChanged", self._current_position_name)
        self.emit(
            "diameterIndexChanged",
            self._current_diameter_index,
            self._diameter_size_list[self._current_diameter_index] / 1000.0,
        )

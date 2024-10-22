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


import logging
from warnings import warn

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2010-2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractAperture(HardwareObject):
    def __init__(self, name):
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

    def get_diameter_size_list(self):
        """
        Returns:
            list: list of diameter sizes in microns
        """
        return self._diameter_size_list

    def get_position_list(self):
        """
        Returns:
            list: list of position names as str
        """
        return self._position_list

    def get_diameter_index(self):
        """
        Returns:
            int: current diameter index
        """
        return self._current_diameter_index

    def set_diameter_index(self, diameter_index):
        """
        Sets active diameter index

        Args:
            diameter_index (int): selected diameter index

        Emits:
            diameterIndexChanged (int, float): current index, diameter in mm
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

    def get_diameter_size(self):
        """
        Returns:
            float: current diameter size in mm
        """
        return self._diameter_size_list[self._current_diameter_index]

    def set_diameter_size(self, diameter_size):
        """
        Args:
            diameter_size (int): selected diameter index
        """
        if diameter_size in self._diameter_size_list:
            self.set_diameter_index(self._diameter_size_list.index(diameter_size))
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Selected diameter is not in the diameter list"
            )

    def get_position_name(self):
        """
        Returns:
            str: current position as str
        """
        return self._current_position_name

    def set_position(self, position_index):
        warn(
            "set_position is deprecated. Use set_position_index(position_index) instead",
            DeprecationWarning,
        )
        self.set_position_index(position_index)

    def set_position_name(self, position_name):
        """
        Sets aperture position based on a position name

        Args:
            position_name (str): selected position
        """
        if position_name in self._position_list:
            self._current_position_name = position_name
            self.emit("valueChanged", self._current_position_name)
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Position %s is not in the position list" % position_name
            )

    def set_position_index(self, position_index):
        """
        Sets aperture position based on a position index

        Args:
            position_index (int): selected position index
        """
        if position_index < len(self._position_list):
            self._current_position_name = self._position_list[position_index]
            self.emit("valueChanged", self._current_position_name)
        else:
            logging.getLogger("HWR").warning(
                "Aperture: Selected position is not in the position list"
            )

    def set_in(self):
        """
        Sets aperture in the beam
        """
        pass

    def set_out(self):
        """
        Removes aperture from the beam
        """
        pass

    def is_out(self):
        """
        Returns:
            bool: True if aperture is in the beam, otherwise returns false
        """
        pass

    def force_emit_signals(self):
        """
        Reemits all signals
        """
        self.emit("valueChanged", self._current_position_name)
        self.emit(
            "diameterIndexChanged",
            self._current_diameter_index,
            self._diameter_size_list[self._current_diameter_index] / 1000.0,
        )

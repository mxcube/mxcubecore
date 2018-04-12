#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.


import logging
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE colaboration"]


class AbstractAperture(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._current_position_name = None
        self._current_diameter_index = None
        self._diameter_size_list = []
        self._position_list = []

    def init(self):
        try:
            self._diameter_size_list = \
                eval(self.getProperty("diameter_size_list"))
        except:
            logging.getLogger("HWR").error(\
                "Aperture: no diameter size list defined")

        try:
            self._position_list = eval(self.getProperty("position_list"))
        except:
            logging.getLogger("HWR").error(\
                "Aperture: no position list defined")

    # Methods to get internal read only variables -----------------------------

    def get_diameter_list(self):
        #TODO rename method to get_diameter_size_list
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

    # Methods to set/get internal read/write variables ------------------------

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
            self.emit('diameterIndexChanged', self._current_diameter_index,
                      self._diameter_size_list[self._current_diameter_index] \
                      / 1000.0)
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected diameter index is not valid")

    def get_diameter_size(self):
        #TODO rename to get_diameter_size_mm
        """
        Returns:
            float: current diameter size in mm
        """
        return self._diameter_size_list[self._current_diameter_index]

    def set_diameter_size(self, diameter_size):
        #TODO rename to set_diameter_size_mm
        """
        Args:
            diameter_size (int): selected diameter index
        """
        if diameter_size in self._diameter_size_list:
            self.set_diameter_index(self._diameter_size_list.index(diameter_size))
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected diameter is not in the diameter list")

    def get_position(self):
        #TODO rename to get_position_name
        """
        Returns:
            str: current position as str
        """
        return self._current_position_name

    def set_position_name(self, position_name):
        """
        Sets aperture position based on a position name

        Args:
            position_name (str): selected position
        """
        if position_name in self._position_list:
            self._current_position_name = position_name
            self.emit('positionChanged', self._current_position_name)
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected position is not in the position list")

    def set_position_index(self, position_index):
        """
        Sets aperture position based on a position index

        Args:
            position_index (int): selected position index
        """
        if position_index < len(self._position_list):
            self._current_position_name = self._position_list[position_index]
            self.emit('positionChanged', self._current_position_name)
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected position is not in the position list")

    # Other methods -----------------------------------------------------------

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

    def update_values(self):
        """
        Reemits all signals
        """
        self.emit('positionChanged', self._current_position_name)
        self.emit('diameterIndexChanged', self._current_diameter_index,
                  self._diameter_size_list[self._current_diameter_index] \
                  / 1000.0)

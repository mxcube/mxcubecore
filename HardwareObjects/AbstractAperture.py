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

        self.__current_position_name = None
        self.__current_diameter_index = None
        self.__diameter_size_list = []
        self.__position_list = []

    def init(self):
        try:
            self.__diameter_size_list = \
                eval(self.getProperty("diameter_size_list"))
        except:
            logging.getLogger("HWR").error(\
                "Aperture: no diameter size list defined")

        try:
            self.__position_list = eval(self.getProperty("position_list"))
        except:
            logging.getLogger("HWR").error(\
                "Aperture: no diameter size list defined")

    # Methods to get internal read only variables -----------------------------

    def get_diameter_list(self):
        #TODO rename method to get_diameter_size_list
        """
        Returns:
            list: list of diameter sizes in microns
        """
        return self.__diameter_size_list

    def get_position_list(self):
        """
        Returns:
            list: list of position names as str
        """
        return self.__position_list

    # Methods to set/get internal read/write variables ------------------------

    def get_diameter_index(self):
        """
        Returns:
            int: current diameter index
        """
        return self.__current_diameter_index

    def set_diameter_index(self, diameter_index):
        """
        Sets active diameter index

        Keyword Args:
            diameter_index (int): selected diameter index

        Emits:
            diameterIndexChanged (int, float): current index, diameter in mm
        """
        self.__current_diameter_index = diameter_index
        self.emit('diameterIndexChanged', self.__current_diameter_index,
                  self.__diameter_size_list[self.__current_diameter_index] \
                  / 1000.0)

    def get_diameter_size(self):
        #TODO rename to get_diameter_size_mm
        """
        Returns:
            float: current diamter size in mm
        """
        return self.__diameter_size_list[self.__current_diameter_index]

    def set_diameter_size(self, diameter_size):
        #TODO rename to set_diameter_size_mm
        """
        Keyword Args:
            diameter_size (int): selected diameter index
        """
        if diameter_size in self.__diameter_size_list:
            self.set_diameter_index(self.__diameter_size_list.index(diameter_size))
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected diamter is not in the diameter list")

    def get_position(self):
        #TODO rename to get_position_name
        """
        Returns:
            str: current position as str
        """
        return self.__current_position_name

    def set_position_name(self, position_name):
        """
        Sets aperture position based on a position name

        Keyword Args:
            position_name (str): selected position
        """
        if position_name in self.__position_list:
            self.__current_position_name = position_name
            self.emit('positionChanged', self.__current_position_name)
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected position is not in the position list")

    def set_position_index(self, position_index):
        """
        Sets aperture position based on a position index

        Keyword Args:
            position_index (int): selected position index
        """
        if position_index < len(self.__position_list):
            self.__current_position_name = self.__position_list[position_index]
            self.emit('positionChanged', self.__current_position_name)
        else:
            logging.getLogger("HWR").warning(\
                "Aperture: Selected position is not in the position list")

    # Other methods -----------------------------------------------------------

    def set_in(self):
        """
        Sets aperture in the beam
        """
        self.set_position("BEAM")

    def set_out(self):
        """
        Removes aperture from the beam
        """
        self.set_position("OFF")

    def is_out(self):
        """
        Returns:
            bool: True if aperture is in the beam, otherwise returns false
        """
        return self.__current_position_name != "BEAM"

    def update_values(self):
        """
        Reemits all signals
        """
        self.emit('positionChanged', self.__current_position_name)
        self.emit('diameterIndexChanged', self.__current_diameter_index,
                  self.__diameter_size_list[self.__current_diameter_index] \
                  / 1000.0)

#
#  Project: MXCuBE
#  https://github.com/mxcube.
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

import logging
from HardwareRepository.HardwareObjects.abstract.AbstractAperture import (
    AbstractAperture,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3"


"""
xml example:

<device class="ApertureMockup">
  <position_list>["BEAM", "OFF", "PARK"]</position_list>
  <diameter_size_list>[5, 10, 20, 30, 50, 100]</diameter_size_list>
</device>
"""

DEFAULT_POSITION_LIST = ("BEAM", "OFF", "PARK")
DEFAULT_DIAMETER_SIZE_LIST = (5, 10, 20, 30, 50, 100)


class ApertureMockup(AbstractAperture):
    def __init__(self, name):
        AbstractAperture.__init__(self, name)

    def init(self):
        try:
            self._diameter_size_list = eval(self.get_property("diameter_size_list"))
        except BaseException:
            self._diameter_size_list = DEFAULT_DIAMETER_SIZE_LIST
            logging.getLogger("HWR").error(
                "Aperture: no diameter size list defined, using default list"
            )

        try:
            self._position_list = eval(self.get_property("position_list"))
        except BaseException:
            self._position_list = DEFAULT_POSITION_LIST
            logging.getLogger("HWR").error(
                "Aperture: no position list defined, using default list"
            )

        self.set_position_index(0)
        self.set_diameter_index(0)

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
        return self._current_position_name != "BEAM"

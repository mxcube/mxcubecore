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

"""BeamstopMockup"""

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["MXCuBE colaboration"]


class BeamstopMockup(HardwareObject):
    """
    Descrip. :
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        HardwareObject.__init__(self, name)

        self.default_size = None
        self.default_distance = None
        self.default_direction = None

    def init(self):
        """
        Descrip. :
        """
        self.default_size = self.getProperty("defaultBeamstopSize")
        self.default_distance = self.getProperty("defaultBeamstopDistance")
        self.default_direction = self.getProperty("defaultBeamstopDirection")

    def get_size(self):
        """
        Descrip. :
        """
        return self.default_size

    def set_distance(self, position):
        self.default_distance = position

    def get_distance(self):
        """
        Descrip. :
        """
        return self.default_distance

    def get_direction(self):
        """
        Descrip. :
        """
        return self.default_direction

    def update_values(self):
        self.emit("beamstopDistanceChanged", (self.default_distance))

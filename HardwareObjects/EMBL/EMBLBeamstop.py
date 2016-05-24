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

"""
EMBLBeamstop
"""

from HardwareRepository.BaseHardwareObjects import Device


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class EMBLBeamstop(Device):
    """
    Descrip. :
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        Device.__init__(self, name)

        self.distance = None
        self.default_size = None
        self.default_distance = None
        self.default_direction = None 

        self.chan_distance = None
        self.chan_position = None

    def init(self):
        """
        Descrip. :
        """
        self.default_beamstop_size = self.getProperty("defaultBeamstopSize")
        self.default_beamstop_distance = self.getProperty("defaultBeamstopDistance")
        self.default_beamstop_direction = self.getProperty("defaultBeamstopDirection")
 
        self.chan_distance = self.getChannelObject('BeamstopDistance')
        if self.chan_distance is not None:
            self.chan_distance.connectSignal("update", self.distance_changed)

        self.chan_position = self.getChannelObject('BeamstopPosition')

    def isReady(self):
        """
        Descrip. :
        """
        return True

    def distance_changed(self, value):
        self.distance = value
        self.emit('beamstopDistanceChanged', (value))

    def moveToPosition(self, name):
        pass
 
    def get_size(self):
        """
        Descrip. :
        """
        return self.default_size

    def set_distance(self, position):
        if self.chan_distance is not None:
            self.chan_distance.setValue(position)
            self.distance_changed(position)

    def get_distance(self):
        """
        Descrip. :
        """
        distance = None
        if self.chan_distance is not None:
            distance = self.chan_distance.getValue()

        if distance is None:
            return self.default_distance
        else:
            return distance

    def get_direction(self):
        """
        Descrip. :
        """
        return self.default_direction

    def get_position(self):
        return self.chan_position.getValue()

    def set_position(self, position):
        self.chan_position.setValue(position)

    def update_values(self):
        self.distance = self.chan_distance.getValue()
        self.emit('beamstopDistanceChanged', (self.distance))

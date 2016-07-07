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
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLBeamstop(Device):
    """
    Descrip. :
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        Device.__init__(self, name)

        self.beamstop_distance = None
        self.default_beamstop_size = None
        self.default_beamstop_distance = None
        self.default_beamstop_direction = None 

        self.chan_beamstop_distance = None

    def init(self):
        """
        Descrip. :
        """
        self.default_beamstop_size = \
             self.getProperty("defaultBeamstopSize")
        self.default_beamstop_distance = \
             self.getProperty("defaultBeamstopDistance")
        self.default_beamstop_direction = \
             self.getProperty("defaultBeamstopDirection")
 
        self.chan_beamstop_distance = \
             self.getChannelObject('BeamstopDistance')
        if self.chan_beamstop_distance is not None:
            self.chan_beamstop_distance.connectSignal("update", 
               self.beamstop_distance_changed)

    def isReady(self):
        """
        Descrip. :
        """
        return True

    def beamstop_distance_changed(self, value):
        self.beamstop_distance = value
        self.emit('beamstopDistanceChanged', (value))

    def set_position(self, position):
        if self.chan_beamstop_distance is not None:
            self.chan_beamstop_distance.setValue(position)
            self.beamstop_distance_changed(position)           

    def moveToPosition(self, name):
        pass
 
    def get_beamstop_size(self):
        """
        Descrip. :
        """
        return self.default_beamstop_size

    def get_beamstop_distance(self):
        """
        Descrip. :
        """
        beamstop_distance = None
        if self.chan_beamstop_distance is not None:
            beamstop_distance = self.chan_beamstop_distance.getValue()

        if beamstop_distance is None:
            return self.default_beamstop_distance
        else:
            return beamstop_distance

    def get_beamstop_direction(self):
        """
        Descrip. :
        """
        return self.default_beamstop_direction

    def update_values(self):
        self.beamstop_distance =  self.chan_beamstop_distance.getValue()
        self.emit('beamstopDistanceChanged', (self.beamstop_distance))
        

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

from HardwareRepository.BaseHardwareObjects import Device


__author__ = "Ivars Karpics"
__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


POSITIONS = ("BEAM", "OFF", "PARK")


class EMBLAperture(Device):
    """Aperture control hwobj uses exporter or Tine channels and commands
       to control aperture position
    """

    def __init__(self, name):
        """Inherited from Device"""
        Device.__init__(self, name)

        self.position = None
        self.current_diameter_index = None
        self.diameter_list = []

        self.chan_diameter_index = None
        self.chan_diameters = None
        self.chan_position = None

    def init(self):
        """Initialization of channels and commands"""

        self.chan_diameters = self.getChannelObject('ApertureDiameters')
        if self.chan_diameters:
            self.diameter_list = self.chan_diameters.getValue()
        else:
            self.diameter_list = [10, 20]

        self.chan_diameter_index = \
            self.getChannelObject('CurrentApertureDiameterIndex')
        if self.chan_diameter_index is not None:
            self.current_diameter_index = self.chan_diameter_index.getValue()
            self.diameter_index_changed(self.current_diameter_index)
            self.chan_diameter_index.connectSignal(\
                 'update', self.diameter_index_changed)
        else:
            self.current_diameter_index = 0

        self.chan_position = self.getChannelObject('AperturePosition')
        if self.chan_position:
            self.position = self.chan_position.getValue()
            self.position_changed(self.position)
            self.chan_position.connectSignal('update', self.position_changed)

    def diameter_index_changed(self, diameter_index):
        """Callback when diameter index has been changed"""
        self.current_diameter_index = diameter_index
        self.emit('diameterIndexChanged', diameter_index,
             self.diameter_list[diameter_index] / 1000.0)

    def get_diameter_size(self):
        """Returns: diameter index as int"""
        return self.diameter_list[self.current_diameter_index] / 1000.0

    def position_changed(self, position):
        """Position change callback"""
        self.position = position
        self.emit('positionChanged', position)

    def set_diameter_index(self, diameter_index):
        """Sets new diameter index

        :param diameter_index: new diameter index
        :type diameter_index: int
        """
        self.chan_diameter_index.setValue(diameter_index)

    def set_diameter(self, diameter_size):
        """Sets new aperture size

        :param diameter_size: new size
        :type diameter_size: int
        """
        self.chan_diameter_index.setValue(\
             self.diameter_list.index(diameter_size))

    def set_position(self, position):
        """Sets new aperture position

        :param diameter_index: new position
        :type diameter_index: str
        """
        self.chan_position.setValue(POSITIONS[position])

    def set_in(self):
        """Sets aperture to the BEAM position"""
        self.chan_position.setValue("BEAM")

    def set_out(self):
        """Sets aperture to the OUT position"""
        self.chan_position.setValue("OFF")

    def is_out(self):
        """Returns True if aperture is on the beam"""
        return self.position != "BEAM"

    def get_diameter_list(self):
        """Returns a list with  available apertures"""
        return self.diameter_list

    def get_position_list(self):
        """Returns a list with available aperture positions"""
        return POSITIONS

    def update_values(self):
        """Reemits hwobj signals"""
        self.diameter_index_changed(self.current_diameter_index)
        self.position_changed(self.position)

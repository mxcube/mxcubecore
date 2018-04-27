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

import gevent
from AbstractAperture import AbstractAperture


__credits__ = ["EMBL Hamburg"]
__category__ = "General"
__license__ = "LGPLv3"


DEFAULT_POSITION_LIST = ("BEAM", "OFF", "PARK")


class EMBLAperture(AbstractAperture):
    """Aperture control hwobj uses exporter or Tine channels and commands
       to control aperture position
    """

    def __init__(self, name):
        """Inherited from Device"""
        AbstractAperture.__init__(self, name)

        self.chan_diameter_index = None
        self.chan_diameters = None
        self.chan_position = None
        self.chan_state = None

    def init(self):
        """Initialization of channels and commands"""

        self._position_list = DEFAULT_POSITION_LIST

        self.chan_diameters = self.getChannelObject('ApertureDiameters')
        if self.chan_diameters:
            self._diameter_size_list = self.chan_diameters.getValue()
        else:
            self._diameter_size_list = [10, 20]

        self.chan_diameter_index = \
            self.getChannelObject('CurrentApertureDiameterIndex')
        if self.chan_diameter_index is not None:
            self._current_diameter_index = self.chan_diameter_index.getValue()
            self.diameter_index_changed(self._current_diameter_index)
            self.chan_diameter_index.connectSignal(\
                 'update', self.diameter_index_changed)
        else:
            self._current_diameter_index = 0

        self.chan_position = self.getChannelObject('AperturePosition')
        if self.chan_position:
            self._current_position_name = self.chan_position.getValue()
            self.current_position_name_changed(self._current_position_name)
            self.chan_position.connectSignal('update', self.current_position_name_changed)

        self.chan_state = self.getChannelObject('State') 

    def diameter_index_changed(self, diameter_index):
        """Callback when diameter index has been changed"""
        self._current_diameter_index = diameter_index
        self.emit('diameterIndexChanged', self._current_diameter_index,
                  self._diameter_size_list[self._current_diameter_index] \
                  / 1000.0)

    def get_diameter_size(self):
        """Returns: diameter size in mm"""
        return self._diameter_size_list[self._current_diameter_index] / 1000.0

    def current_position_name_changed(self, position):
        """Position change callback"""
        if position != "UNKNOWN":
            self.set_position_name(position) 

    def set_diameter_index(self, diameter_index):
        """Sets new diameter index

        :param diameter_index: new diameter index
        :type diameter_index: int
        """
        self.chan_diameter_index.setValue(diameter_index)

    def set_diameter(self, diameter_size, timeout=None):
        """Sets new aperture size

        :param diameter_size: new size
        :type diameter_size: int
        """
        diameter_index = self._diameter_size_list.index(diameter_size)
        self.chan_diameter_index.setValue(diameter_index)
        #if timeout:
        #    while diameter_index != self.chan_diameter_index.getValue():
        #         gevent.sleep(0.1)

    def set_position_index(self, position):
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

    def wait_ready(self, timeout=20):
        with gevent.Timeout(timeout, Exception("Timeout waiting for status ready")):
            while self.chan_state.getValue() != "Ready":
                   gevent.sleep(0.1)

    def is_out(self):
        """Returns True if aperture is on the beam"""
        return self._current_position_name != "BEAM"

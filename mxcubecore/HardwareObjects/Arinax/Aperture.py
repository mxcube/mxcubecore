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

"""Inherited from AbstracAperture"""
import gevent

from mxcubecore.HardwareObjects.abstract.AbstractAperture import (
    AbstractAperture,
)

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


DEFAULT_POSITION_LIST = ("BEAM", "OFF", "PARK")


class Aperture(AbstractAperture):
    """Aperture control hwobj uses exporter or Tine channels and commands
       to control aperture position
    """

    def __init__(self, name):
        """Inherited from AbstractAperture"""
        AbstractAperture.__init__(self, name)

        self.chan_diameter_index = None
        self.chan_diameters = None
        self.chan_position = None
        self.chan_state = None

    def init(self):
        """
        Connects to necessary channels
        Returns:
        """
        self._position_list = DEFAULT_POSITION_LIST

        self.chan_diameters = self.get_channel_object("ApertureDiameters")
        if self.chan_diameters:
            self._diameter_size_list = self.chan_diameters.get_value()
        else:
            self._diameter_size_list = (10, 20)

        self.chan_diameter_index = self.get_channel_object(
            "CurrentApertureDiameterIndex"
        )
        if self.chan_diameter_index is not None:
            self._current_diameter_index = self.chan_diameter_index.get_value()
            self.diameter_index_changed(self._current_diameter_index)
            self.chan_diameter_index.connect_signal(
                "update", self.diameter_index_changed
            )
        else:
            self._current_diameter_index = 0

        self.chan_position = self.get_channel_object("AperturePosition")
        if self.chan_position:
            self._current_position_name = self.chan_position.get_value()
            self.current_position_name_changed(self._current_position_name)
            self.chan_position.connect_signal(
                "update", self.current_position_name_changed
            )
        self.chan_state = self.get_channel_object("State")

    def diameter_index_changed(self, diameter_index):
        """Callback when diameter index has been changed"""
        self._current_diameter_index = diameter_index
        self.emit(
            "diameterIndexChanged",
            self._current_diameter_index,
            self._diameter_size_list[self._current_diameter_index] / 1000.0,
        )

    def current_position_name_changed(self, position):
        """
        Position change callback

        Args:
            position: aperture position (str)
        Returns:
        """
        if position != "UNKNOWN":
            self.set_position_name(position)

    def set_diameter_index(self, diameter_index):
        """
        Sets aperture diameter

        Args:
            diameter_index: diameter index (int)
        Returns:
        """
        super().set_diameter_index(diameter_index)
        self.chan_diameter_index.set_value(diameter_index)

    def set_diameter(self, diameter_size, timeout=None):
        """
        Sets new aperture size

        Args:
            diameter_size: diameter size in microns (int)
            timeout: wait timeout is seconds
        Returns:
        """
        diameter_index = self._diameter_size_list.index(diameter_size)
        self.chan_diameter_index.set_value(diameter_index)
        self.chan_diameter_index.update()

    def set_position_index(self, position_index):
        """
        Sets new aperture position

        Args:
            position_index: position index (int)
        Returns:
        """
        self.chan_position.set_value(self._position_list[position_index])
        self.chan_position.update()

    def set_in(self):
        """
        Sets aperture to the BEAM position

        Returns:
        """
        self.chan_position.set_value("BEAM")
        self.chan_position.update()

    def set_out(self):
        """Sets aperture to the OUT position

        Returns:
        """
        self.chan_position.set_value("OFF")
        self.chan_position.update()

    def wait_ready(self, timeout=20):
        """Waits till aperture is ready

        Returns:
        """
        super(Aperture, self).wait_ready(timeout=20)

    def is_out(self):
        """Returns True if aperture is on the beam

        Returns: True if is in, otherwise returns False
        """
        return self._current_position_name != "BEAM"

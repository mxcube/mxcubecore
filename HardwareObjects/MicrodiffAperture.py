# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Aperture as Expoorter motor"""

from HardwareRepository.HardwareObjects.ExporterMotor import ExporterMotor


class MicrodiffAperture(ExporterMotor):
    """MicrodiffAperture class"""

    def __init__(self, name):
        ExporterMotor.__init__(self, name)
        self.predefined_positions = []
        self._exporter = None
        self.position_channel = None
        self.motor_state = None
        self.aperture_factor = None

    def init(self):
        """Initialize the aperture"""
        ExporterMotor.init(self)
        _exporter_address = self.getProperty("exporter_address")
        """
        self.position_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "aperture_position",
            },
            "CurrentApertureDiameterIndex"
        )
        if self.position_channel:
            self.get_value()
            self.position_channel.connectSignal("update", self.update_value)
        """

        self.motor_state = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "aperture_state",
            },
            "State",
        )

        if self.motor_state:
            self.motor_state.connectSignal("update", self._update_state)

        self.predefined_positions = self._exporter.read_property("ApertureDiameters")
        if 300 not in self.predefined_positions:
            self.predefined_positions.append(300)

        self.update_state()

    def get_limits(self):
        """Returns aperture low and high limits.
        Returns:
            (tuple): two int tuple (low limit, high limit).
        """
        self._limits = (min(self.predefined_positions), max(self.predefined_positions))

        return self._limits

    def get_aperture_factor(self):
        _current_aperture = self.get_label()
        for diameter in self["diameter"]:
            if str(_current_aperture) == str(diameter.getProperty("name")):
                _factor = diameter.getProperty("aperture_factor")
        return _factor

    def _set_value(self, value_index):
        """Move motor to absolute value. Wait the move to finish.
        Args:
            value (float): target value
        """
        value = self.predefined_positions.index(int(value_index))
        self.position_channel.set_value(value)

    def get_label(self):
        return self.predefined_positions[self.get_value()]

    def get_aperture_size(self):
        return self.predefined_positions[self.get_value()]

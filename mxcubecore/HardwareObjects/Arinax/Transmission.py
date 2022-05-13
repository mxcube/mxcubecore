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
"""Transmission """

from HardwareRepository.HardwareObjects.abstract.AbstractTransmission import (
    AbstractTransmission,
)

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class Transmission(AbstractTransmission):
    """Transmission class"""

    unit = "%"

    def __init__(self, name):
        super(Transmission, self).__init__(name)
        self._transmission = None
        self.transmission_channel = None

    def init(self):
        """Initialise from the config"""
        super(Transmission, self).init()
        self.transmission_channel = self.get_channel_object("transmissionChannel")
        self.transmission_channel.connectSignal("update", self.update_value)
        self._transmission = self.get_value()

    def _set_value(self, value):
        """Set the transmission.
        Args:
            value(float): Transmission [%]
        """
        self.transmission_channel.setValue(value)
        self.update_value(value)

        # Busy is set by AbstractActuator, simply set state to ready
        # when done so that ready event is set.
        self.update_state(self.STATES.READY)

    def get_value(self):
        """Get the real transmission value
        Returns:
            (float): Transmission [%]
        """
        return self.transmission_channel.getValue()
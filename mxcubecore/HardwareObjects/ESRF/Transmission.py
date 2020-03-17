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
"""Transmission with bliss """

from HardwareRepository.BaseHardwareObjects import HardwareObject


class Transmission(HardwareObject):
    """Transmission class"""

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.__transmission = None
        self.labels = []
        self.indexes = []
        self.attno = 0

    def init(self):
        """Initialise from the config"""
        module_name = self.getProperty("module_name")
        ctrl = self.getObjectByRole("controller")
        self.__transmission = getattr(ctrl, module_name)

    def is_ready(self):
        """Always True
        Returns:
            (bool): True
        """
        return True

    def get_att_config(self):
        """Get the attenuators configuration"""
        self.attno = len(self["filter"])

        for att_i in range(self.attno):
            obj = self["filter"][att_i]
            self.labels.append(obj.label)
            self.indexes.append(obj.index)

    def get_att_state(self):
        """Get the attenuators position
        Returns:
            (int): value
        """
        return self.__transmission.matt.pos_read()

    def _set_value(self, trans):
        """Set the transmission. Emit valueChanged.
        Args:
            trans(float): Transmission [%]
        """
        self.__transmission.set(trans)
        self.emit("valueChanged", self.get_value())

    def _update(self):
        self.emit("attStateChanged", self.get_att_state())

    def toggle(self, attenuator_index):
        """Toggle the attenuatots
        Args:
            attenuator_index(int): Index of the attenuator, starting from 0.
        """
        idx = self.indexes[attenuator_index]
        if self.is_in(attenuator_index):
            self.__transmission.matt.mattout(idx)
        else:
            self.__transmission.matt.mattin(idx)
        self._update()

    def get_value(self):
        """Get the real transmission value
        Returns:
            (float): Transmission [%]
        """
        return self.__transmission.get()

    def get_limits(self):
        """Get the limits
        Returns:
            (tuple): Transmission limits
        """
        return 0, 100

    def is_in(self, attenuator_index):
        """Check the attenuator position
        Args:
            attenuator_index(int): Index of the attenuator, starting from 0.
        Returns:
            (bool): True if in, False if out.
        """
        curr_bits = self.get_att_state()
        idx = self.indexes[attenuator_index]
        return bool((1 << idx) & curr_bits)

# encoding: utf-8
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

"""
BeamDefinerMockup class
"""

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

class BeamDefinerMockup(AbstractNState):

    def __init__(self, *args):
        super().__init__(*args)
        self.beam_size_hor = None
        self.beam_size_ver = None

    def init(self):
        AbstractNState.init(self)

        self.beam_size_hor = self.get_object_by_role("beam_size_hor")
        self.beam_size_ver = self.get_object_by_role("beam_size_ver")
        self.beam_size_hor.connect

        self.connect(self.beam_size_hor, "valueChanged", self.motors_changed)
        self.connect(self.beam_size_ver, "valueChanged", self.motors_changed)

    def motors_changed(self, value):
        _val = self.get_value()
        self.emit("valueChanged", _val)

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        return self.STATES.READY

    def get_value(self):
        """Get the device value
        Returns:
        """
        try:
            hor = int(self.beam_size_hor.get_value())
            ver = int(self.beam_size_ver.get_value())
            _val = f"{hor}x{ver}"
            en = self.value_to_enum(_val)
            return en
        except ValueError:
            return -1

    def set_value(self, val):
        """Set the beam size.
        Args:
            size_x: horizontal size
            size_y: vertical size
        """
        size_x, size_y = val.split('x')
        self.beam_size_hor._move(float(size_x))
        self.beam_size_ver._move(float(size_y))

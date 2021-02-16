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


from HardwareRepository.HardwareObjects.abstract.AbstractSlits import AbstractSlits


__credits__ = ["MXCuBE collaboration"]


class LNLSSlits(AbstractSlits):
    def __init__(self, *args):
        AbstractSlits.__init__(self, *args)

    def init(self):
        # Slits start wide open
        self._value = [1.00, 1.00]
        self._min_limits = [0.001, 0.001]
        self._max_limits = [1, 1]

    def set_horizontal_gap(self, value):
        self._value[0] = value
        self.emit("valueChanged", self._value)

    def set_vertical_gap(self, value):
        self._value[1] = value
        self.emit("valueChanged", self._value)

    def stop_horizontal_gap_move(self):
        return

    def stop_vertical_gap_move(self):
        return

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

from AbstractAperture import AbstractAperture


__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


"""
xml example:

<device class="ApertureMockup">
  <position_list>["BEAM", "OFF", "PARK"]</position_list>
  <diameter_size_list>[5, 10, 20, 30, 50, 100]</diameter_size_list>
</device>
"""


class ApertureMockup(AbstractAperture):

    def __init__(self, name):
        AbstractAperture.__init__(self, name)

    def init(self):
        AbstractAperture.init(self)

        self.set_position_index(0)
        self.set_diameter_index(0)

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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


from HardwareRepository.HardwareObjects.abstract.AbstractSampleView import (
    AbstractSampleView,
)


class SampleView(AbstractSampleView):
    def __init__(self, name):
        AbstractSampleView.__init__(self, name)

    def init(self):
        self._camera = self.getObjectByRole("camera")
        self._shapes = self.getObjectByRole("shapes")
        self._focus = self.getObjectByRole("focus")
        self._zoom = self.getObjectByRole("zoom")
        self._frontlight = self.getObjectByRole("frontlight")
        self._backlight = self.getObjectByRole("backlight")

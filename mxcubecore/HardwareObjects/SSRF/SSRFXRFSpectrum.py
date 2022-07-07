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

import time

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import (
    AbstractXRFSpectrum,
)
from mxcubecore.BaseHardwareObjects import HardwareObject


spectrum_test_data = [
    0,
    20,
    340,
    70,
    100,
    110,
    120,
    200,
    200,
    210,
    1600,
    210,
    200,
    200,
    200,
    250,
    300,
    200,
    100,
    0,
    0,
    0,
    90,
]


class SSRFXRFSpectrum(AbstractXRFSpectrum, HardwareObject):
    def __init__(self, name):
        AbstractXRFSpectrum.__init__(self)
        HardwareObject.__init__(self, name)
        self.fluo_hwo = None

    def init(self):
        """ Initialize all command, channel and hardware objects """

        self.fluo_hwo = self.get_object_by_role("fluodet")

    def isConnected(self):
        return True

    def can_spectrum(self):
        """ Returns true if run spectrum command can be executed """
        return True

    def execute_spectrum_command(self, count_time, filename, adjust_transmission=True):
        # self.spectrum_data = spectrum_test_data
        self.spectrum_data = self.fluo_hwo.read_roi_data()
        self.spectrum_command_finished()

    def cancel_spectrum(self, *args):
        """
        Cancels acquisition
        """
        pass

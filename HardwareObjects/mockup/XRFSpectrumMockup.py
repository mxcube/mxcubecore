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

import time

from HardwareRepository.HardwareObjects.abstract.AbstractXRFSpectrum import (
    AbstractXRFSpectrum,
)
from HardwareRepository.BaseHardwareObjects import HardwareObject


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


class XRFSpectrumMockup(AbstractXRFSpectrum, HardwareObject):
    def __init__(self, name):
        AbstractXRFSpectrum.__init__(self)
        HardwareObject.__init__(self, name)

    def init(self):
        pass

    def isConnected(self):
        return True

    def can_spectrum(self):
        return True

    def execute_spectrum_command(self, count_time, filename, adjust_transmission):
        self.spectrum_data = spectrum_test_data
        time.sleep(3)
        self.spectrum_command_finished()

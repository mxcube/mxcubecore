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


from time import sleep

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import (
    AbstractXRFSpectrum,
)


__copyright__ = """ Copyright © 2010-2023 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class XRFSpectrumMockup(AbstractXRFSpectrum):

    def _execute_xrf_spectrum(self, count_time=None, filename=None):
        """Specific XRF acquisition procedure.
        Args:
            integration_time (float): MCA integration time [s].
            filename (str): Data file (full path).
        """
        count_time = count_time or self.default_integration_time
        sleep(count_time)
        return True

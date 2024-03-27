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
Mockup file to define _execute_xrf_spectrum method
"""

from time import sleep

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import (
    AbstractXRFSpectrum,
)


__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class XRFSpectrumMockup(AbstractXRFSpectrum):
    """Overload the abstract method"""

    def _execute_xrf_spectrum(self, integration_time=None, filename=None):
        """Specific XRF acquisition procedure.

        Args:
            integration_time (float): MCA integration time [s].
            filename (str): Data file (full path).
        """
        integration_time = integration_time or self.default_integration_time
        sleep(integration_time)
        return True

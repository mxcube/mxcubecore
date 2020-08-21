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

"""LNLS Energy"""

from HardwareRepository.HardwareObjects.abstract.AbstractEnergy import (
    AbstractEnergy)
from HardwareRepository.HardwareObjects.LNLS.EPICSActuator import EPICSActuator

# Default energy value (keV)
DEFAULT_VALUE = 0.0


class LNLSEnergy(EPICSActuator, AbstractEnergy):
    """LNLSEnergy class"""

    def init(self):
        """Initialise default properties"""
        super(LNLSEnergy, self).init()

        if self.default_value is None:
            self.default_value = DEFAULT_VALUE
            self.update_value(DEFAULT_VALUE)
        self.update_state(self.STATES.READY)

    def set_value(self):
        """Override method."""
        pass

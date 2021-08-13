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

from mxcubecore.HardwareObjects.EMBL.TINEMotor import TINEMotor

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLResolution(TINEMotor):
    """
    Based on the TineMotor. After the move command executes additional
    commands.
    """

    def __init__(self, name):
        TINEMotor.__init__(self, name)

    def get_limits(self):
        return self._nominal_limits

    def get_value(self):
        return self._nominal_value

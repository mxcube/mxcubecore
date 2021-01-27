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
EMBLPiezoMotor
"""

import logging

from mxcubecore.hardware_objects.EMBL.TINEMotor import TINEMotor

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLPiezoMotor(TINEMotor):
    """
    Based on the TineMotor. After the move command executes additional
    commands.
    """

    def __init__(self, name):
        TINEMotor.__init__(self, name)

        self.cmd_move_first = None
        self.cmd_move_second = None

    def init(self):
        TINEMotor.init(self)
        self.cmd_move_first = self.get_command_object("cmdMoveFirst")
        self.cmd_move_second = self.get_command_object("cmdMoveSecond")

    def _set_value(self, value):
        """Moves motor to the target position

        :param value: target position
        :type value: float
        :return: None
        """
        self.cmd_move_first(value)
        self.cmd_move_second(1)

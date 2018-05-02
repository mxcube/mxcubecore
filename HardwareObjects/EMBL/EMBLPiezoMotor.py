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

import logging
import gevent

from TINEMotor import TINEMotor


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3"
__category__ = "Motor"

class EMBLPiezoMotor(TINEMotor):

    def __init__(self, name):
        TINEMotor.__init__(self, name)

        self.cmd_move_first = None
        self.cmd_move_second = None
  
    def init(self):
        TINEMotor.init(self)
        self.cmd_move_first = self.getCommandObject("cmdMoveFirst")
        self.cmd_move_second = self.getCommandObject("cmdMoveSecond")

    def move(self, target, wait=None, timeout=None):
        """
        Descript. :
        """
        if target == float('nan'):
            logging.getLogger().debug('Refusing to move %s to target nan'%(self.objName))
        else:
            self.cmd_move_first(target)
            self.cmd_move_second(1)

    def getMotorMnemonic(self):
        """
        Descript. :
        """
        return "EMBLPiezoMotor"

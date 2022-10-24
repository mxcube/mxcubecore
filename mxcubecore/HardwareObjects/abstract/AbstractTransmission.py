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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Abstract Transmission
Set the unit as [%] and the limits to 0-100.
"""

import abc
from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator


__copyright__ = """ Copyright © 2010- 2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractTransmission(AbstractActuator):
    """Abstract Transmission

    The value of the transmission is in % (float or int).
    If the transmission has no continuous values,
    beamlines should provide the nearest achievable one"""

    unit = "%"

    __metaclass__ = abc.ABCMeta

    def init(self):
        super().init()
        self.update_limits((0, 100))

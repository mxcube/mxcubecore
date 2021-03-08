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
"""
Convert exporter states to HardwareObject states
"""

from enum import Enum
from mxcubecore.BaseHardwareObjects import HardwareObjectState

__copyright__ = """ Copyright © 2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class ExporterStates(Enum):
    """Convert exporter states to HardwareObject amd Motor states"""

    UNKNOWN = HardwareObjectState.UNKNOWN
    STANDBY = HardwareObjectState.WARNING
    DISABLE = HardwareObjectState.WARNING
    ALARM = HardwareObjectState.WARNING
    BUSY = HardwareObjectState.BUSY
    MOVING = HardwareObjectState.BUSY
    RUNNING = HardwareObjectState.BUSY
    INITIALIZING = HardwareObjectState.BUSY
    READY = HardwareObjectState.READY
    ON = HardwareObjectState.READY
    OFF = HardwareObjectState.READY
    CLOSED = HardwareObjectState.READY
    OPEN = HardwareObjectState.READY
    FAULT = HardwareObjectState.FAULT
    INVALID = HardwareObjectState.FAULT
    OFFLINE = HardwareObjectState.FAULT

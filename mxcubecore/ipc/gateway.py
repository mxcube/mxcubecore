# encoding: utf-8
#
#  Project name: MXCuBE
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

"""IPCGateway: a beamline object for IPC-facing methods that don't belong
to any single HardwareObject acts as a replacement for XMLRPCServer.
"""

from mxcubecore.BaseHardwareObjects import HardwareObject


class IPCGateway(HardwareObject):
    """See module docstring."""

    def ping(self, message: str = "") -> str:
        """Echo `message` back as "pong: <message>"."""
        return f"pong: {message}"

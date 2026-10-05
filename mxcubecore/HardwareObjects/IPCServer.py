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

"""Re-export so IPCServer can be referenced as `class="IPCServer"` from XML
config. mxcubecore.HardwareObjectFileParser resolves an XML `class=`
attribute as a bare module name that must live directly under
mxcubecore/HardwareObjects/, with its class named the same as the module -
the real implementation lives in mxcubecore/ipc/server.py, alongside the
rest of the IPC layer, not under HardwareObjects/.

YAML config can (and should) reference the real module directly instead:
`class: mxcubecore.ipc.server.IPCServer`.
"""

from mxcubecore.ipc.server import IPCServer

__all__ = ["IPCServer"]

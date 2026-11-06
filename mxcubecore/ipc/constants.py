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

"""Constants for the mxcubecore IPC layer - for now just the shared logger."""

from mxcubecore.log import hwr_log

#: The single logger ("HWR.ipc") everything in mxcubecore.ipc logs to:
#: transports, whitelist dispatch (every method call), the server's
#: session/auth handling, and the signal -> event bridge (every event).
logger = hwr_log.getChild("ipc")

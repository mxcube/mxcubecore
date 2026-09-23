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

"""IPC layer exposing a whitelist of HardwareObject methods to third-party
clients, over a JSON-RPC/TCP or NanoMQ (MQTT) transport.

See IPC_FORMAT.md for the wire format.
"""

from mxcubecore.ipc.constants import (
    IPC_FORMAT_VERSION,
    ErrorCode,
)
from mxcubecore.ipc.models import (
    IPCError,
    IPCEvent,
    IPCRequest,
    IPCResponse,
)
from mxcubecore.ipc.server import IPCServer
from mxcubecore.ipc.whitelist import (
    IPCWhitelistError,
    build_whitelist,
    dispatch,
    get_role,
    ipc_method,
    resolve_role_path,
)

__all__ = [
    "IPC_FORMAT_VERSION",
    "ErrorCode",
    "IPCError",
    "IPCEvent",
    "IPCRequest",
    "IPCResponse",
    "IPCServer",
    "IPCWhitelistError",
    "build_whitelist",
    "dispatch",
    "get_role",
    "ipc_method",
    "resolve_role_path",
]

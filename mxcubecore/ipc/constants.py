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

"""Constants for the mxcubecore IPC layer: wire format version, error codes,
and the shared logger.

The wire-format ones (IPC_FORMAT_VERSION, the reserved method names and
ErrorCode) are mirrored in the separate mxcube-ipc-client package
(mxcube_ipc_client/constants.py) - keep the two in step.
"""

from enum import IntEnum

from mxcubecore.log import hwr_log

#: Version of the IPC wire format defined by mxcubecore/ipc/IPC_FORMAT.md
IPC_FORMAT_VERSION = "0.0.1"

#: Method name reserved for the authentication handshake.
AUTH_METHOD = "_auth"

#: Method name reserved for whitelist self-description (see
#: mxcubecore.ipc.whitelist.describe() and IPC_FORMAT.md section 6).
DESCRIBE_METHOD = "_describe"

#: Method names reserved for the debug bypass (see mxcubecore.ipc.debug and
#: IPC_FORMAT.md section 7). Disabled by default - only handled at all if
#: IPCServer's `allow_debug_calls` config is true.
DEBUG_LIST_ROLES_METHOD = "_debug_list_roles"
DEBUG_DESCRIBE_ROLE_METHOD = "_debug_describe_role"
DEBUG_CALL_METHOD = "_debug_call"

#: The single logger ("HWR.ipc") everything in mxcubecore.ipc logs to:
#: transports, whitelist dispatch (every method call), the server's
#: session/auth handling, and the signal -> event bridge (every event).
logger = hwr_log.getChild("ipc")


class ErrorCode(IntEnum):
    """Error codes carried in an :class:`mxcubecore.ipc.models.IPCError`.

    The negative range below -32000 mirrors the JSON-RPC 2.0 reserved codes
    so a plain JSON-RPC client can interpret them, as defined by the
    JSON-RPC 2.0 spec.
    """

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    NOT_AUTHENTICATED = -32000
    METHOD_NOT_WHITELISTED = -32001
    VALIDATION_ERROR = -32002
    CLIENT_ALREADY_CONNECTED = -32003
    DEBUG_CALLS_DISABLED = -32004

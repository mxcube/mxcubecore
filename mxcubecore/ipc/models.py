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

"""Pydantic envelope models for the mxcubecore IPC wire format.

See IPC_FORMAT.md for the full wire format description. The envelope is
JSON-RPC 2.0 shaped and shared verbatim by both transports (JSON-RPC/TCP and
NanoMQ) so the core dispatch logic in mxcubecore.ipc.server never has to
know which transport carried a message.
"""

from typing import (
    Any,
    Dict,
    Literal,
    Optional,
    Union,
)

from pydantic import BaseModel, Field


class _JsonRpc(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"


class IPCError(BaseModel):
    """Error payload carried in an IPCErrorResponse."""

    code: int
    message: str
    data: Optional[Any] = None


class IPCRequest(_JsonRpc):
    """A command sent by the client to invoke one whitelisted method."""

    id: Union[str, int]
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class IPCResponse(_JsonRpc):
    """Successful reply to an IPCRequest."""

    id: Union[str, int]
    result: Any = None


class IPCErrorResponse(_JsonRpc):
    """Error reply to an IPCRequest.

    `id` is None when the request's id couldn't be determined (e.g. parse error).
    """

    id: Optional[Union[str, int]] = None
    error: IPCError


class IPCEvent(_JsonRpc):
    """A server-initiated notification (no `id`, no reply expected)."""

    method: str
    params: Dict[str, Any] = Field(default_factory=dict)

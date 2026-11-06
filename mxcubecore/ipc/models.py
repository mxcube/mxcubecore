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
    Optional,
    Union,
)

from pydantic import BaseModel, Field


class IPCError(BaseModel):
    """Error payload carried in an IPCResponse."""

    code: int
    message: str
    data: Optional[Any] = None


class IPCRequest(BaseModel):
    """A command sent by the client to invoke one whitelisted method."""

    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class IPCResponse(BaseModel):
    """The server's reply to one IPCRequest.

    Exactly one of `result`/`error` is set, mirroring JSON-RPC 2.0.
    """

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[IPCError] = None


class IPCEvent(BaseModel):
    """A server-initiated notification (no `id`, no reply expected)."""

    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)

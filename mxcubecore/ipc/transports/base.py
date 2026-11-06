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

"""Transport-agnostic interface driven by mxcubecore.ipc.server.IPCServer.

A concrete transport owns connection handling, TLS and message framing;
it knows nothing about the raw JSON IPCRequest/IPCResponse/IPCEvent or
the whitelist IPCServer owns the session/auth layer and all envelope
handling on top of whatever raw JSON frames a transport delivers.
"""

import abc
from typing import (
    Callable,
    Optional,
)


class Transport(abc.ABC):
    """Common interface for the JSON-RPC/TCP and NanoMQ transports."""

    @abc.abstractmethod
    def start(
        self,
        on_message: Callable[[str, str], None],
        on_connect: Callable[[str, Optional[str]], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        """Start listening for (or connecting to) clients.

        `on_message(session_id, raw_json)` is called for every inbound
        frame.

        `on_disconnect(session_id)` when a client's connection is
        torn down at the transport level

        `on_connect(session_id, peer)` is called when a connection is
        established; `peer` is a human-readable "ip:port (hostname)" string
        for transports that have one (JSON-RPC/TCP), or None for transports
        that don't (NanoMQ has no per-connection socket only a `_client_id`
        in each message).
        """

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the transport and release any resources (sockets, MQTT
        client loop etc.).
        """

    @abc.abstractmethod
    def send(self, session_id: str, raw_json: str) -> None:
        """Send one frame to the given session, if it is still connected."""

    @abc.abstractmethod
    def has_active_client(self) -> bool:
        """Whether a client is currently connected."""

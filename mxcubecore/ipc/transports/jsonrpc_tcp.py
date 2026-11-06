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

"""JSON-RPC 2.0 over a raw, newline-delimited TCP socket, optionally TLS.

Built on gevent.server.StreamServer to match the gevent-based concurrency
model as we are using (PyDispatcher/gevent).
"""

import socket
import ssl
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
)

from gevent.lock import Semaphore
from gevent.server import StreamServer

from mxcubecore.ipc.constants import logger
from mxcubecore.ipc.transports.base import Transport

# Rejection sent (then the socket is closed) to any connection attempt
# while another client is already connected - written directly, since the
# session/whitelist layer above hasn't seen this connection at all yet.
_CLIENT_ALREADY_CONNECTED_FRAME = (
    b'{"jsonrpc": "2.0", "id": null, "error": '
    b'{"code": -32003, "message": "Client already connected"}}\n'
)


def _describe_peer(address: Tuple[str, int]) -> str:
    """ "ip:port (hostname)", for logging. Reverse DNS is best-effort - a
    client on an unresolvable address still connects fine, it just logs
    without a hostname.
    """
    ip, port = address[0], address[1]
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except OSError:
        return f"{ip}:{port}"
    return f"{ip}:{port} ({hostname})"


class JSONRPCTCPTransport(Transport):
    """Single-client JSON-RPC/TCP transport."""

    def __init__(
        self,
        host: str,
        port: int,
        tls_cert_path: Optional[str] = None,
        tls_key_path: Optional[str] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._tls_cert_path = tls_cert_path
        self._tls_key_path = tls_key_path

        self._server: Optional[StreamServer] = None
        # gevent socket file objects (`sock.makefile()`), keyed by session id
        self._files: Dict[str, Any] = {}
        # Responses are written from the connection's own greenlet, IPCEvents
        # from whichever greenlet emitted the signal. A write can yield
        # mid-frame (full socket buffer), and a second greenlet then entering
        # the same BufferedWriter raises "RuntimeError: reentrant call" - so
        # every frame is written and flushed under this lock.
        self._write_lock = Semaphore()

        self._on_message: Optional[Callable[[str, str], None]] = None
        self._on_connect: Optional[Callable[[str], None]] = None
        self._on_disconnect: Optional[Callable[[str], None]] = None

    def start(
        self,
        on_message: Callable[[str, str], None],
        on_connect: Callable[[str], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        self._on_message = on_message
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

        ssl_args = {}
        if self._tls_cert_path and self._tls_key_path:
            ssl_args = {
                "certfile": self._tls_cert_path,
                "keyfile": self._tls_key_path,
                "ssl_version": ssl.PROTOCOL_TLS_SERVER,
            }
        else:
            logger.warning(
                "JSON-RPC IPC transport starting without TLS - configure "
                "tls_cert_path/tls_key_path for a real deployment"
            )

        self._server = StreamServer(
            (self._host, self._port), self._handle_connection, **ssl_args
        )
        self._server.start()
        logger.info("JSON-RPC/TCP IPC transport listening on %s", self._server.address)

    @property
    def address(self):
        """The actual bound (host, port)."""
        return self._server.address

    def stop(self) -> None:
        if self._server is not None:
            self._server.stop()
            self._server = None
            logger.info("JSON-RPC/TCP IPC transport stopped")
        self._files = {}

    def has_active_client(self) -> bool:
        return bool(self._files)

    def send(self, session_id: str, raw_json: str) -> None:
        sock_file = self._files.get(session_id)
        if sock_file is None:
            return
        try:
            with self._write_lock:
                sock_file.write(raw_json.encode("utf-8") + b"\n")
                sock_file.flush()
        except OSError:
            logger.warning("Failed to send to IPC session %s, dropping it", session_id)
            self._files.pop(session_id, None)

    def _handle_connection(self, sock, address) -> None:
        if self._files:
            logger.warning(
                "Rejecting IPC connection from %s: already connected", address
            )
            try:
                sock.sendall(_CLIENT_ALREADY_CONNECTED_FRAME)
            finally:
                sock.close()
            return

        session_id = str(uuid.uuid4())
        sock_file = sock.makefile(mode="rwb")
        self._files[session_id] = sock_file

        self._on_connect(session_id, _describe_peer(address))
        try:
            for line in sock_file:
                line = line.strip()
                if not line:
                    continue
                self._on_message(session_id, line.decode("utf-8"))
        finally:
            self._files.pop(session_id, None)
            self._on_disconnect(session_id)

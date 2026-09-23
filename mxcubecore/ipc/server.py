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

"""IPCServer: a HardwareObject that exposes a whitelist of other
HardwareObjects' methods to a single external client, over either a
JSON-RPC/TCP or a NanoMQ (MQTT) transport.

Configured like any other beamline object (see mxcubecore/configuration/
mockup/ipc-server-mockup.yml for an example) and resolves whitelisted
targets through the standard `mxcubecore.HardwareRepository.beamline`
singleton, exactly like any other role lookup in this codebase.
"""

import ast
import secrets
import threading
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import (
    ConfiguredObject,
    HardwareObject,
)
from mxcubecore.ipc import debug
from mxcubecore.ipc.constants import (
    AUTH_METHOD,
    DEBUG_CALL_METHOD,
    DEBUG_DESCRIBE_ROLE_METHOD,
    DEBUG_LIST_ROLES_METHOD,
    DESCRIBE_METHOD,
    ErrorCode,
    logger,
)
from mxcubecore.ipc.dispatcher_bridge import DispatcherBridge
from mxcubecore.ipc.events import (
    EventEntry,
    build_events,
    describe_events,
)
from mxcubecore.ipc.models import (
    IPCError,
    IPCEvent,
    IPCRequest,
    IPCResponse,
)
from mxcubecore.ipc.transports.base import Transport
from mxcubecore.ipc.whitelist import (
    IPCWhitelistError,
    build_whitelist,
    describe,
    dispatch,
)


class IPCServer(HardwareObject):
    """Beamline-configured IPC server. See IPC_FORMAT.md for the wire
    format and mxcubecore/ipc/whitelist.py for the whitelist rules.
    """

    class HOConfig(ConfiguredObject.HOConfig):
        # "jsonrpc" or "nanomq"
        transport = "jsonrpc"

        # jsonrpc transport settings - bind to localhost by default; set to
        # a routable address explicitly if external access is needed.
        host = "127.0.0.1"
        port = 9999
        tls_cert_path = None
        tls_key_path = None

        # nanomq (MQTT) transport settings - 1883 is the standard MQTT
        # plaintext port, matching this transport's plaintext-by-default
        # behavior (a missing tls_ca_cert_path only warns, same as
        # jsonrpc's tls_cert_path/tls_key_path). Set broker_port to 8883
        # (the standard MQTT-over-TLS port) alongside tls_ca_cert_path for
        # a real deployment.
        broker_host = "localhost"
        broker_port = 1883
        topic_prefix = "mxcube/ipc"
        tls_ca_cert_path = None

        # Shared-secret token required by the "_auth" handshake before any
        # whitelisted method can be called.
        auth_token = None

        # The global whitelist: flat list of "role.method" strings.
        allowed_methods: list = []

        # HardwareObject signals to forward as IPCEvents:
        # [{"role": ..., "signal": ..., "method": ..., "args": [...]}, ...]
        # "args" (optional) declares one type expression per positional
        # signal argument - see mxcubecore/ipc/events.py.
        events: list = []

        # DANGER - off by default. If true, any authenticated client can
        # invoke the "_debug_call" bypass: ANY method, on ANY resolvable
        # role, with ANY arguments - no whitelist check, no pydantic
        # validation. See mxcubecore/ipc/debug.py and IPC_FORMAT.md
        # section 7. Only ever enable this for local, trusted exploration.
        allow_debug_calls = False

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._transport: Optional[Transport] = None
        self._registry: Dict[str, Any] = {}
        self._events: Dict[str, EventEntry] = {}
        self._authenticated_session: Optional[str] = None
        self._bridge = DispatcherBridge(self._push_event)
        # The gevent hub init() ran in - all session state and transport
        # writes happen there (see _push_event).
        self._hub: Any = None
        # True only once init() has fully succeeded, incl. the transport
        # actually starting - `self._transport is not None` alone isn't
        # enough to tell: it gets assigned before `.start()` is called, so
        # it's already set even if `.start()` itself is what failed.
        self.started = False

    def _get_list_property(self, name: str) -> List[Any]:
        """Read a list/list-of-dict config property.

        YAML config gives back a native list already; XML config always
        gives back a string, in the same "Python literal syntax" convention
        already used for `exports`/`commands` elsewhere in this codebase
        (BaseHardwareObjects.py:667-669, BeamlineActions.py) - e.g.
        `<allowed_methods>["role.method"]</allowed_methods>`.
        """
        value = self.get_property(name, [])
        if isinstance(value, str):
            value = ast.literal_eval(value.strip()) if value.strip() else []
        return list(value or [])

    def init(self) -> None:
        try:
            self._do_init()
        except Exception:
            # HardwareRepository.load_from_yaml()/parse_xml() swallow any
            # exception raised here for a non-top-level role - it only
            # shows up as "Error in IPCServer.init()" in the printed load
            # table, with the actual cause discarded completely. Log it
            # here, with the traceback, before it disappears upstream.
            logger.exception("IPCServer failed to initialize")
            raise

    def _do_init(self) -> None:
        super().init()
        self._hub = gevent.get_hub()
        self._registry = build_whitelist(
            HWR.beamline, self._get_list_property("allowed_methods")
        )
        self._events = build_events(HWR.beamline, self._get_list_property("events"))

        transport_kind = self.get_property("transport", "jsonrpc")
        if transport_kind == "jsonrpc":
            from mxcubecore.ipc.transports.jsonrpc_tcp import JSONRPCTCPTransport

            self._transport = JSONRPCTCPTransport(
                host=self.get_property("host", "127.0.0.1"),
                port=self.get_property("port", 9999),
                tls_cert_path=self.get_property("tls_cert_path"),
                tls_key_path=self.get_property("tls_key_path"),
            )
        elif transport_kind == "nanomq":
            from mxcubecore.ipc.transports.nanomq import NanoMQTransport

            self._transport = NanoMQTransport(
                host=self.get_property("broker_host", "localhost"),
                port=self.get_property("broker_port", 1883),
                topic_prefix=self.get_property("topic_prefix", "mxcube/ipc"),
                tls_ca_cert_path=self.get_property("tls_ca_cert_path"),
            )
        else:
            raise ValueError(f"Unknown IPC transport: {transport_kind!r}")

        if self.get_property("allow_debug_calls", False):
            logger.warning(
                "*** IPC DEBUG BYPASS IS ENABLED (allow_debug_calls: true) - "
                "any authenticated client can invoke ANY method on ANY "
                "resolvable role with ANY arguments, with no whitelist check "
                "and no pydantic validation. Only use this for local, "
                "trusted exploration - see IPC_FORMAT.md section 7. ***"
            )

        for entry in self._events.values():
            self._bridge.subscribe(
                entry.sender, entry.signal, entry.method, entry.check_args
            )

        self._transport.start(
            on_message=self._on_message,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )
        self.started = True
        logger.info("IPC server started: transport=%s", transport_kind)

    def stop(self) -> None:
        if self._transport is not None:
            self._transport.stop()
            self._transport = None
        self._bridge.unsubscribe_all()
        logger.info("IPC server stopped")
        super().stop()

    def _on_connect(self, session_id: str, peer: Optional[str]) -> None:
        logger.info(
            "IPC client connecting: %s (%s)", session_id, peer or "unknown peer"
        )

    def _on_disconnect(self, session_id: str) -> None:
        if session_id == self._authenticated_session:
            self._authenticated_session = None
        logger.info("IPC client disconnected: %s", session_id)

    def _push_event(self, method: str, params: Dict[str, Any]) -> None:
        if threading.get_ident() != self._hub.thread_ident:
            # Emitted from a real OS thread (mxcubecore patches gevent with
            # thread=False, and some HardwareObjects emit from their own
            # threads) - gevent sockets, locks and session state must not be
            # touched from there, so re-run this in a hub greenlet instead.
            self._hub.loop.run_callback_threadsafe(
                gevent.spawn, self._push_event, method, params
            )
            return
        if self._authenticated_session is None or self._transport is None:
            logger.debug(
                "IPC event %s(%s) dropped: no authenticated client", method, params
            )
            return
        logger.info("IPC event: %s(%s)", method, params)
        event = IPCEvent(method=method, params=params)
        self._transport.send(self._authenticated_session, event.model_dump_json())

    def _on_message(self, session_id: str, raw_json: str) -> None:
        try:
            request = IPCRequest.model_validate_json(raw_json)
        except Exception as exc:
            logger.warning("IPC request parse error from %s: %s", session_id, exc)
            self._send_error(session_id, None, ErrorCode.PARSE_ERROR, str(exc))
            return

        if request.method == AUTH_METHOD:
            self._handle_auth(session_id, request)
            return

        if self._authenticated_session != session_id:
            logger.warning(
                "IPC call %r from unauthenticated session %s",
                request.method,
                session_id,
            )
            self._send_error(
                session_id, request.id, ErrorCode.NOT_AUTHENTICATED, "Not authenticated"
            )
            return

        if request.method == DESCRIBE_METHOD:
            self._handle_describe(session_id, request)
            return

        if request.method in (
            DEBUG_LIST_ROLES_METHOD,
            DEBUG_DESCRIBE_ROLE_METHOD,
            DEBUG_CALL_METHOD,
        ):
            self._handle_debug(session_id, request)
            return

        try:
            result = dispatch(
                HWR.beamline, self._registry, request.method, request.params
            )
        except IPCWhitelistError as exc:
            # dispatch() already logged this at WARNING.
            self._send_error(
                session_id, request.id, ErrorCode.METHOD_NOT_WHITELISTED, str(exc)
            )
            return
        except Exception as exc:
            # dispatch() already logged the failure (with traceback) at
            # ERROR - just note the client-facing outcome here.
            self._send_error(
                session_id, request.id, ErrorCode.VALIDATION_ERROR, str(exc)
            )
            return

        response = IPCResponse(id=request.id, result=result)
        self._transport.send(session_id, response.model_dump_json())

    def _handle_auth(self, session_id: str, request: IPCRequest) -> None:
        if (
            self._authenticated_session is not None
            and self._authenticated_session != session_id
        ):
            logger.warning(
                "IPC auth from %s rejected: %s already connected",
                session_id,
                self._authenticated_session,
            )
            self._send_error(
                session_id,
                request.id,
                ErrorCode.CLIENT_ALREADY_CONNECTED,
                "Another client is already connected",
            )
            return

        expected_token = self.get_property("auth_token")
        token = request.params.get("token", "")

        if not expected_token or not secrets.compare_digest(
            str(token), str(expected_token)
        ):
            logger.warning("IPC auth from %s rejected: invalid token", session_id)
            self._send_error(
                session_id, request.id, ErrorCode.NOT_AUTHENTICATED, "Invalid token"
            )
            return

        self._authenticated_session = session_id
        logger.info("IPC auth from %s succeeded", session_id)
        response = IPCResponse(id=request.id, result={"authenticated": True})
        self._transport.send(session_id, response.model_dump_json())

    def _handle_describe(self, session_id: str, request: IPCRequest) -> None:
        response = IPCResponse(
            id=request.id,
            result={
                "methods": describe(self._registry),
                "events": describe_events(self._events),
            },
        )
        self._transport.send(session_id, response.model_dump_json())

    def _handle_debug(self, session_id: str, request: IPCRequest) -> None:
        if not self.get_property("allow_debug_calls", False):
            logger.warning(
                "IPC debug call %r from %s rejected: allow_debug_calls is disabled",
                request.method,
                session_id,
            )
            self._send_error(
                session_id,
                request.id,
                ErrorCode.DEBUG_CALLS_DISABLED,
                "Debug calls are disabled (allow_debug_calls is false)",
            )
            return

        role = request.params.get("role", "")
        try:
            if request.method == DEBUG_LIST_ROLES_METHOD:
                result = debug.list_roles(HWR.beamline, role)
            elif request.method == DEBUG_DESCRIBE_ROLE_METHOD:
                result = debug.describe_role(HWR.beamline, role)
            else:
                result = debug.debug_call(
                    HWR.beamline,
                    role,
                    request.params["method"],
                    request.params.get("args"),
                    request.params.get("kwargs"),
                )
        except Exception as exc:
            logger.exception("IPC debug call %s failed", request.method)
            self._send_error(session_id, request.id, ErrorCode.INTERNAL_ERROR, str(exc))
            return

        logger.warning(
            "IPC DEBUG BYPASS: %s from %s: %s -> %s",
            request.method,
            session_id,
            request.params,
            result,
        )
        response = IPCResponse(id=request.id, result=result)
        self._transport.send(session_id, response.model_dump_json())

    def _send_error(
        self,
        session_id: str,
        request_id: Optional[Union[str, int]],
        code: ErrorCode,
        message: str,
    ) -> None:
        response = IPCResponse(
            id=request_id, error=IPCError(code=int(code), message=message)
        )
        self._transport.send(session_id, response.model_dump_json())

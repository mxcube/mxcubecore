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

"""IPC transport over MQTT, for use with a NanoMQ broker (or any MQTT
3.1.1/5-compliant broker. We are using the paho-mqtt client).

MQTT itself has no notion of "a connection" the way a TCP socket does, so
single-client enforcement happens purely at the message layer: every
message must carry a `_client_id`, and the first one seen claims the
session until a message announcing that same `_client_id` arrives on the
`<topic_prefix>/disconnect` topic.

A well-behaved client publishes that message itself right before it
disconnects cleanly, and *also* registers it as an MQTT Last Will
(`client.will_set(...)`) so the broker publishes it on the client's
behalf if it disconnects uncleanly (crash, network loss) see IPC_FORMAT.md
section 3. Without either, the slot is only freed when the whole
IPCServer/transport is stopped.
"""

import json
from collections import deque
from typing import (
    Any,
    Callable,
    Deque,
    Optional,
    Tuple,
)

import gevent
import paho.mqtt.client as mqtt
from gevent.event import Event

from mxcubecore.ipc.constants import logger
from mxcubecore.ipc.transports.base import Transport

_CLIENT_ALREADY_CONNECTED_FRAME = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32003, "message": "Client already connected"},
    }
)


class NanoMQTransport(Transport):
    """Single-client MQTT transport for a NanoMQ (or compatible) broker."""

    def __init__(
        self,
        host: str,
        port: int,
        topic_prefix: str,
        tls_ca_cert_path: Optional[str] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._request_topic = f"{topic_prefix}/request"
        self._response_topic = f"{topic_prefix}/response"
        self._event_topic = f"{topic_prefix}/event"
        self._disconnect_topic = f"{topic_prefix}/disconnect"
        self._tls_ca_cert_path = tls_ca_cert_path

        self._client: Optional[mqtt.Client] = None
        self._active_client_id: Optional[str] = None

        # (topic, payload) pairs appended by paho's thread, drained by
        # `_worker` in the gevent hub. deque.append/popleft are atomic, so
        # the deque itself needs no lock; `_inbox_ready` is a gevent Event
        # and is therefore only ever touched from the hub thread (the paho
        # thread sets it via run_callback_threadsafe).
        self._inbox: Deque[Tuple[str, bytes]] = deque()
        self._inbox_ready = Event()
        self._processing = False
        self._hub: Any = None
        self._worker: Optional[gevent.Greenlet] = None
        # Broker connection state, only for logging: warn once per outage,
        # and stay quiet about the disconnect stop() itself causes.
        self._broker_reachable = True
        self._stopping = False

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

        # start() runs in the hub thread (IPCServer.init()), so this is the
        # hub every inbound message is handed over to.
        self._hub = gevent.get_hub()
        self._worker = gevent.spawn(self._process_inbox)

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self._tls_ca_cert_path:
            self._client.tls_set(ca_certs=self._tls_ca_cert_path)
        else:
            logger.warning(
                "NanoMQ IPC transport starting without TLS - configure "
                "tls_ca_cert_path for a real deployment"
            )

        self._client.on_message = self._handle_message
        self._client.on_connect = self._handle_broker_connect
        self._client.on_connect_fail = self._handle_broker_connect_fail
        self._client.on_disconnect = self._handle_broker_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        # Not connect(): that makes a single attempt and raises if the broker
        # isn't up yet. connect_async() + loop_start() keeps retrying in
        # paho's thread - on startup and after the broker goes away - so the
        # server and the broker can be started in either order.
        self._stopping = False
        self._client.connect_async(self._host, self._port)
        self._client.loop_start()
        logger.info(
            "NanoMQ IPC transport connecting to broker at %s:%s",
            self._host,
            self._port,
        )

    def stop(self) -> None:
        if self._client is not None:
            self._stopping = True
            # disconnect() before loop_stop(), so the loop is still running to
            # actually send the DISCONNECT packet.
            self._client.disconnect()
            self._client.loop_stop()
            self._client = None
            logger.info("NanoMQ IPC transport disconnected")
        if self._worker is not None:
            self._worker.kill()
            self._worker = None
        self._inbox.clear()
        if self._active_client_id is not None:
            client_id, self._active_client_id = self._active_client_id, None
            self._on_disconnect(client_id)

    def has_active_client(self) -> bool:
        return self._active_client_id is not None

    def send(self, session_id: str, raw_json: str) -> None:
        if session_id != self._active_client_id or self._client is None:
            return
        self._client.publish(self._response_topic, raw_json)

    def publish_event(self, raw_json: str) -> None:
        """Push a server-initiated IPCEvent frame, outside the
        request/response cycle.
        """
        if self._client is not None:
            self._client.publish(self._event_topic, raw_json)

    def _handle_broker_connect(
        self, client, userdata, flags, reason_code, properties
    ) -> None:
        if reason_code.is_failure:
            # e.g. bad credentials - paho keeps retrying, but it won't help.
            logger.error(
                "NanoMQ IPC transport: broker at %s:%s refused the connection: %s",
                self._host,
                self._port,
                reason_code,
            )
            return

        # Subscribed on every (re)connect, not once: a restarted broker has
        # forgotten our subscriptions, and without them the server would sit
        # connected but never see a request.
        client.subscribe(self._request_topic)
        client.subscribe(self._disconnect_topic)
        self._broker_reachable = True
        logger.info(
            "NanoMQ IPC transport connected to %s:%s, subscribed to %s and %s",
            self._host,
            self._port,
            self._request_topic,
            self._disconnect_topic,
        )

    def _handle_broker_connect_fail(self, client, userdata) -> None:
        if self._broker_reachable:
            self._broker_reachable = False
            logger.warning(
                "NanoMQ IPC transport: can't reach broker at %s:%s, retrying "
                "in the background (IPC requests can't arrive until it's up)",
                self._host,
                self._port,
            )
        else:
            logger.debug("NanoMQ IPC transport: broker still unreachable, retrying")

    def _handle_broker_disconnect(
        self, client, userdata, flags, reason_code, properties
    ) -> None:
        if self._stopping:
            return
        self._broker_reachable = False
        logger.warning(
            "NanoMQ IPC transport: lost connection to broker at %s:%s (%s), "
            "reconnecting",
            self._host,
            self._port,
            reason_code,
        )

    def _handle_message(self, client, userdata, msg) -> None:
        """paho's on_message callback - runs in paho's network thread, so
        it only hands the message over to the hub (see module docstring).
        """
        self._inbox.append((msg.topic, msg.payload))
        self._hub.loop.run_callback_threadsafe(self._inbox_ready.set)

    def _process_inbox(self) -> None:
        while True:
            self._inbox_ready.wait()
            self._inbox_ready.clear()
            while self._inbox:
                self._processing = True
                topic, raw = self._inbox.popleft()
                try:
                    self._process_message(topic, raw)
                except Exception:
                    logger.exception("Error processing IPC message on %s", topic)
                finally:
                    self._processing = False

    def _process_message(self, topic: str, raw: bytes) -> None:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.warning("Dropping malformed IPC message on %s", topic)
            return

        client_id = payload.get("_client_id")
        if not client_id:
            logger.warning("Dropping IPC message with no _client_id")
            return

        if topic == self._disconnect_topic:
            self._handle_disconnect_message(client_id)
            return

        if self._active_client_id is None:
            self._active_client_id = client_id
            # No per-connection socket at this layer, so unlike the
            # JSON-RPC/TCP transport there is no *authoritative* peer
            # address to report - `_client_host` (if present) is whatever
            # the client itself claims, same trust level as `_client_id`.
            peer = payload.get("_client_host")
            self._on_connect(client_id, f"{peer} (self-reported)" if peer else None)
        elif client_id != self._active_client_id:
            logger.warning(
                "Rejecting IPC message from %s: %s already connected",
                client_id,
                self._active_client_id,
            )
            self._client.publish(self._response_topic, _CLIENT_ALREADY_CONNECTED_FRAME)
            return

        self._on_message(client_id, raw.decode("utf-8"))

    def _handle_disconnect_message(self, client_id: str) -> None:
        """A `{"_client_id": ...}` message on the disconnect topic - either
        published by the client itself right before it disconnects
        cleanly, or by the broker on the client's behalf (its registered
        MQTT Last Will) if it disconnected uncleanly.
        """
        if client_id != self._active_client_id:
            # Stale/unrelated announcement - not the currently active
            # client, nothing to release.
            return

        self._active_client_id = None
        logger.info("IPC client disconnected: %s", client_id)
        self._on_disconnect(client_id)

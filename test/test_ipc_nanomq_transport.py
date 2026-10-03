"""NanoMQ (MQTT) transport tests.

No real MQTT broker is available in CI, so `paho.mqtt.client.Client` is
mocked out entirely: messages are delivered by calling the transport's
`_handle_message` from a separate OS thread (exactly what paho's network
thread does when a message arrives), and assertions read back what got
`publish()`-ed.
"""

import json
import threading
from unittest.mock import MagicMock, patch

import gevent
import pytest

from mxcubecore.ipc.server import IPCServer

AUTH_TOKEN = "s3cr3t"  # noqa: S105


def _mqtt_message(payload: dict, topic: str = "mxcube/ipc/request"):
    msg = MagicMock()
    msg.topic = topic
    msg.payload = json.dumps(payload).encode("utf-8")
    return msg


@pytest.fixture
def ipc_server(beamline):
    with patch("mxcubecore.ipc.transports.nanomq.mqtt.Client") as client_cls:
        mock_client = MagicMock()
        client_cls.return_value = mock_client

        server = IPCServer("ipc_test")
        server._config = IPCServer.HOConfig(
            transport="nanomq",
            broker_host="localhost",
            broker_port=1883,
            topic_prefix="mxcube/ipc",
            auth_token=AUTH_TOKEN,
            allowed_methods=["ipc_gateway.ping"],
            events=[],
        )
        server.init()
        server._mock_client = mock_client
        try:
            yield server
        finally:
            server.stop()


def _deliver(transport, msg) -> None:
    """Deliver `msg` the way paho does - from its own thread - then wait
    until the transport's hub worker has fully processed it.
    """
    thread = threading.Thread(target=transport._handle_message, args=(None, None, msg))
    thread.start()
    thread.join()
    with gevent.Timeout(5):
        while transport._inbox or transport._processing:
            gevent.sleep(0.001)


def _last_published_response(mock_client) -> dict:
    topic, payload = mock_client.publish.call_args[0]
    assert topic == "mxcube/ipc/response"
    return json.loads(payload)


def test_call_without_auth_is_rejected(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ipc_gateway.ping",
                "params": {},
                "_client_id": "client-a",
            }
        ),
    )

    response = _last_published_response(ipc_server._mock_client)
    assert response["error"]["code"] == -32000


def test_auth_then_call_succeeds(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
                "_client_id": "client-a",
            }
        ),
    )
    assert _last_published_response(ipc_server._mock_client)["result"] == {
        "authenticated": True
    }

    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ipc_gateway.ping",
                "params": {"message": "hello"},
                "_client_id": "client-a",
            }
        ),
    )
    assert _last_published_response(ipc_server._mock_client)["result"] == "pong: hello"


def test_second_client_id_is_rejected(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
                "_client_id": "client-a",
            }
        ),
    )

    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ipc_gateway.ping",
                "params": {},
                "_client_id": "client-b",
            }
        ),
    )
    assert _last_published_response(ipc_server._mock_client)["error"]["code"] == -32003


def test_message_without_client_id_is_dropped(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message({"jsonrpc": "2.0", "id": 1, "method": "ipc_gateway.ping"}),
    )
    ipc_server._mock_client.publish.assert_not_called()


def test_disconnect_message_releases_slot_for_next_client(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
                "_client_id": "client-a",
            }
        ),
    )
    assert transport.has_active_client()

    _deliver(
        transport,
        _mqtt_message({"_client_id": "client-a"}, topic="mxcube/ipc/disconnect"),
    )
    assert not transport.has_active_client()

    # A different client can now authenticate.
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
                "_client_id": "client-b",
            }
        ),
    )
    assert _last_published_response(ipc_server._mock_client)["result"] == {
        "authenticated": True
    }


def test_disconnect_message_from_inactive_client_is_ignored(ipc_server):
    transport = ipc_server._transport
    _deliver(
        transport,
        _mqtt_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
                "_client_id": "client-a",
            }
        ),
    )

    # A disconnect announcement for someone who was never (or is no longer)
    # the active client shouldn't evict the real active client.
    _deliver(
        transport,
        _mqtt_message({"_client_id": "client-b"}, topic="mxcube/ipc/disconnect"),
    )
    assert transport.has_active_client()


def test_messages_are_processed_in_the_hub_in_arrival_order(ipc_server):
    transport = ipc_server._transport
    hub_thread = threading.get_ident()
    seen = []

    def _on_message(client_id, raw_json):
        seen.append((threading.get_ident(), json.loads(raw_json)["id"]))

    transport._on_message = _on_message
    for request_id in range(20):
        transport._inbox.append(
            (
                "mxcube/ipc/request",
                _mqtt_message({"id": request_id, "_client_id": "a"}).payload,
            )
        )
    _deliver(transport, _mqtt_message({"id": 20, "_client_id": "a"}))

    assert seen == [(hub_thread, request_id) for request_id in range(21)]


# -- broker connection -----------------------------------------------------


def _reason(name: str):
    from paho.mqtt.packettypes import PacketTypes
    from paho.mqtt.reasoncodes import ReasonCode

    return ReasonCode(PacketTypes.CONNACK, name)


def test_start_connects_in_background_and_waits_for_broker(ipc_server):
    """No blocking connect() - a broker that isn't up yet must not make the
    IPCServer fail to start - and no subscribing until actually connected.
    """
    mock_client = ipc_server._mock_client
    mock_client.connect.assert_not_called()
    mock_client.connect_async.assert_called_once_with("localhost", 1883)
    mock_client.loop_start.assert_called_once()
    mock_client.subscribe.assert_not_called()


def test_subscribes_on_every_connect(ipc_server):
    transport = ipc_server._transport
    mock_client = ipc_server._mock_client
    expected = [(("mxcube/ipc/request",),), (("mxcube/ipc/disconnect",),)]

    transport._handle_broker_connect(mock_client, None, None, _reason("Success"), None)
    assert mock_client.subscribe.call_args_list == expected

    # A restarted broker has forgotten the subscriptions - they must be
    # made again on the reconnect.
    mock_client.subscribe.reset_mock()
    transport._handle_broker_disconnect(
        mock_client, None, None, _reason("Success"), None
    )
    transport._handle_broker_connect(mock_client, None, None, _reason("Success"), None)
    assert mock_client.subscribe.call_args_list == expected


def test_refused_connection_does_not_subscribe(ipc_server, caplog):
    transport = ipc_server._transport
    mock_client = ipc_server._mock_client

    transport._handle_broker_connect(
        mock_client, None, None, _reason("Not authorized"), None
    )

    mock_client.subscribe.assert_not_called()
    assert "refused the connection" in caplog.text


def test_unreachable_broker_warns_once_per_outage(ipc_server, caplog):
    transport = ipc_server._transport
    mock_client = ipc_server._mock_client

    def warnings():
        return [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "reach broker" in r.getMessage()
        ]

    for _ in range(3):
        transport._handle_broker_connect_fail(mock_client, None)
    assert len(warnings()) == 1

    transport._handle_broker_connect(mock_client, None, None, _reason("Success"), None)
    transport._handle_broker_connect_fail(mock_client, None)
    assert len(warnings()) == 2


def test_lost_connection_warns_but_stop_does_not(ipc_server, caplog):
    transport = ipc_server._transport
    mock_client = ipc_server._mock_client

    transport._handle_broker_disconnect(
        mock_client, None, None, _reason("Unspecified error"), None
    )
    assert "lost connection to broker" in caplog.text

    caplog.clear()
    transport._stopping = True
    transport._handle_broker_disconnect(
        mock_client, None, None, _reason("Success"), None
    )
    assert "lost connection to broker" not in caplog.text


def test_stop_disconnects_before_stopping_the_loop(ipc_server):
    mock_client = ipc_server._mock_client
    ipc_server._transport.stop()

    calls = [name for name, _, _ in mock_client.mock_calls]
    assert calls.index("disconnect") < calls.index("loop_stop")

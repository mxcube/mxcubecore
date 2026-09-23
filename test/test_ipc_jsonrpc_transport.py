import json
import socket
import threading

import gevent
import pytest

from mxcubecore.dispatcher import dispatcher
from mxcubecore.ipc.server import IPCServer

AUTH_TOKEN = "s3cr3t"  # noqa: S105


@pytest.fixture
def ipc_server(beamline):
    server = IPCServer("ipc_test")
    server._config = IPCServer.HOConfig(
        transport="jsonrpc",
        host="127.0.0.1",
        port=0,
        auth_token=AUTH_TOKEN,
        allowed_methods=[
            "ipc_gateway.ping",
            "diffractometer.omega.set_value",
            "diffractometer.omega.get_value",
        ],
        events=[
            {
                "role": "procedure",
                "signal": "test_signal",
                "method": "procedure.test_signal",
            },
            {
                "role": "diffractometer.omega",
                "signal": "valueChanged",
                "method": "diffractometer.omega.valueChanged",
                "args": ["float"],
            },
        ],
    )
    server.init()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def ipc_server_debug(beamline):
    """Same as ipc_server, but with the debug bypass explicitly enabled."""
    server = IPCServer("ipc_test_debug")
    server._config = IPCServer.HOConfig(
        transport="jsonrpc",
        host="127.0.0.1",
        port=0,
        auth_token=AUTH_TOKEN,
        allowed_methods=[],
        events=[],
        allow_debug_calls=True,
    )
    server.init()
    try:
        yield server
    finally:
        server.stop()


def _connect(address):
    sock = socket.create_connection(address, timeout=5)
    return sock, sock.makefile(mode="rwb")


def _send(sock_file, message: dict) -> None:
    sock_file.write((json.dumps(message) + "\n").encode("utf-8"))
    sock_file.flush()


def _recv(sock_file) -> dict:
    line = sock_file.readline()
    assert line, "connection closed with no response"
    return json.loads(line.decode("utf-8"))


def _recv_response(sock_file) -> dict:
    """Like _recv, but skips over any IPCEvent frames (no "id") first -
    for calls that are also subscribed to their own events: e.g.
    a blocking set_value (timeout=None) fires several "valueChanged" events
    before dispatch() returns and the actual response gets sent.
    """
    while True:
        frame = _recv(sock_file)
        if "method" not in frame:
            return frame


def test_call_without_auth_is_rejected(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {"jsonrpc": "2.0", "id": 1, "method": "ipc_gateway.ping", "params": {}},
        )
        response = _recv(sock_file)
        assert response["error"]["code"] == -32000
    finally:
        sock.close()


def test_auth_then_call_succeeds(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        auth_response = _recv(sock_file)
        assert auth_response["result"] == {"authenticated": True}

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ipc_gateway.ping",
                "params": {"message": "hello"},
            },
        )
        response = _recv(sock_file)
        assert response["result"] == "pong: hello"
    finally:
        sock.close()


def test_wrong_token_is_rejected(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": "wrong"},
            },
        )
        response = _recv(sock_file)
        assert response["error"]["code"] == -32000
    finally:
        sock.close()


def test_second_concurrent_client_is_rejected(ipc_server):
    sock1, sock_file1 = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file1,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        assert _recv(sock_file1)["result"] == {"authenticated": True}

        sock2 = socket.create_connection(ipc_server._transport.address, timeout=5)
        try:
            data = sock2.recv(4096)
            response = json.loads(data.decode("utf-8"))
            assert response["error"]["code"] == -32003
        finally:
            sock2.close()
    finally:
        sock1.close()


def test_describe_returns_whitelist_schema(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        assert _recv(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file, {"jsonrpc": "2.0", "id": 1, "method": "_describe", "params": {}}
        )
        response = _recv(sock_file)

        methods = response["result"]["methods"]
        assert set(methods) == {
            "ipc_gateway.ping",
            "diffractometer.omega.set_value",
            "diffractometer.omega.get_value",
        }
        assert methods["ipc_gateway.ping"]["request_schema"]["title"] == "PingRequest"

        events = response["result"]["events"]
        assert set(events) == {
            "procedure.test_signal",
            "diffractometer.omega.valueChanged",
        }
        assert events["procedure.test_signal"]["args_schema"] is None
        omega_changed = events["diffractometer.omega.valueChanged"]
        assert omega_changed["args"] == ["float"]
        assert omega_changed["args_schema"]["prefixItems"] == [{"type": "number"}]
    finally:
        sock.close()


def test_call_via_nested_role_path(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        assert _recv(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "diffractometer.omega.set_value",
                "params": {"value": 15.0, "timeout": None},
            },
        )
        response = _recv_response(sock_file)
        assert response["result"] is None

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "diffractometer.omega.get_value",
                "params": {},
            },
        )
        response = _recv_response(sock_file)
        assert response["result"] == 15.0
    finally:
        sock.close()


def test_event_from_nested_role_is_pushed(ipc_server, beamline):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        assert _recv(sock_file)["result"] == {"authenticated": True}

        omega = beamline.diffractometer.get_object_by_role("omega")
        dispatcher.send("valueChanged", omega, 7.0)
        gevent.sleep(0.1)

        event = _recv(sock_file)
        assert event["method"] == "diffractometer.omega.valueChanged"
        assert event["params"] == {"args": [7.0]}
    finally:
        sock.close()


def test_describe_without_auth_is_rejected(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file, {"jsonrpc": "2.0", "id": 1, "method": "_describe", "params": {}}
        )
        response = _recv(sock_file)
        assert response["error"]["code"] == -32000
    finally:
        sock.close()


def test_event_is_pushed_to_authenticated_client(ipc_server, beamline):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "_auth",
                "params": {"token": AUTH_TOKEN},
            },
        )
        assert _recv(sock_file)["result"] == {"authenticated": True}

        dispatcher.send("test_signal", beamline.procedure, "some_value")
        gevent.sleep(0.1)

        event = _recv(sock_file)
        assert event["method"] == "procedure.test_signal"
        assert event["params"] == {"args": ["some_value"]}
    finally:
        sock.close()


def _auth(sock_file, token=AUTH_TOKEN):
    _send(
        sock_file,
        {"jsonrpc": "2.0", "id": 0, "method": "_auth", "params": {"token": token}},
    )
    return _recv(sock_file)


def test_concurrent_events_are_not_interleaved(ipc_server, beamline):
    """Several greenlets emitting large events at once - big enough that a
    write blocks on a full socket buffer and yields mid-frame - must still
    produce whole, separate frames. (Without the transport's write lock
    the second writer hits "RuntimeError: reentrant call", which the
    dispatcher swallows - so its event is silently lost.)
    """
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        def _emit(tag):
            for index in range(5):
                dispatcher.send(
                    "test_signal",
                    beamline.procedure,
                    f"{tag}{index}:" + tag * 2_000_000,
                )

        emitters = [gevent.spawn(_emit, tag) for tag in "ab"]
        # Don't read yet: let both emitters fill the socket buffer and block.
        gevent.sleep(0.2)
        received = []
        while len(received) < 10:
            frame = _recv(sock_file)
            if frame.get("method") == "procedure.test_signal":
                received.append(frame["params"]["args"][0].split(":")[0])
        received.sort()
        gevent.joinall(emitters, raise_error=True)

        assert received == sorted(f"{tag}{index}" for tag in "ab" for index in range(5))
    finally:
        sock.close()


def test_event_emitted_from_another_thread_is_pushed(ipc_server, beamline):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        send = ipc_server._transport.send
        send_threads = []

        def _recording_send(*args):
            send_threads.append(threading.get_ident())
            send(*args)

        ipc_server._transport.send = _recording_send
        thread = threading.Thread(
            target=dispatcher.send,
            args=("test_signal", beamline.procedure, "from_thread"),
        )
        thread.start()
        thread.join()

        event = _recv(sock_file)
        assert event["method"] == "procedure.test_signal"
        assert event["params"] == {"args": ["from_thread"]}
        # ...and was written from the hub, never from the emitting thread.
        assert send_threads == [threading.get_ident()]
    finally:
        sock.close()


def test_debug_call_disabled_by_default(ipc_server):
    sock, sock_file = _connect(ipc_server._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "_debug_list_roles",
                "params": {},
            },
        )
        response = _recv(sock_file)
        assert response["error"]["code"] == -32004
    finally:
        sock.close()


def test_debug_list_roles_when_enabled(ipc_server_debug):
    sock, sock_file = _connect(ipc_server_debug._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file,
            {"jsonrpc": "2.0", "id": 1, "method": "_debug_list_roles", "params": {}},
        )
        response = _recv(sock_file)
        assert "procedure" in response["result"]["roles"]
        assert "diffractometer" in response["result"]["roles"]
    finally:
        sock.close()


def test_debug_describe_role_when_enabled(ipc_server_debug):
    sock, sock_file = _connect(ipc_server_debug._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "_debug_describe_role",
                "params": {"role": "diffractometer.omega"},
            },
        )
        response = _recv(sock_file)
        assert response["result"]["class"] == "MotorMockup"
        assert "set_value" in response["result"]["methods"]
    finally:
        sock.close()


def test_debug_call_when_enabled(ipc_server_debug):
    sock, sock_file = _connect(ipc_server_debug._transport.address)
    try:
        assert _auth(sock_file)["result"] == {"authenticated": True}

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "_debug_call",
                "params": {
                    "role": "diffractometer.omega",
                    "method": "set_value",
                    "kwargs": {"value": 77.0, "timeout": None},
                },
            },
        )
        assert _recv(sock_file)["result"] is None

        _send(
            sock_file,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "_debug_call",
                "params": {"role": "diffractometer.omega", "method": "get_value"},
            },
        )
        response = _recv(sock_file)
        assert response["result"] == 77.0
    finally:
        sock.close()


def test_debug_call_requires_auth(ipc_server_debug):
    sock, sock_file = _connect(ipc_server_debug._transport.address)
    try:
        _send(
            sock_file,
            {"jsonrpc": "2.0", "id": 1, "method": "_debug_list_roles", "params": {}},
        )
        response = _recv(sock_file)
        assert response["error"]["code"] == -32000
    finally:
        sock.close()
